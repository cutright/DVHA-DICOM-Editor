#!/usr/bin/env python
# -*- coding: utf-8 -*-

# main.py
"""
The main file for DVHA DICOM Editor
"""
# Copyright (c) 2020 Dan Cutright
# This file is part of DVHA DICOM Editor, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVHA-DICOM-Editor


import wx
from os.path import isdir, basename, join
from dvhaedit.data_table import DataTable
from dvhaedit.dicom_editor import DICOMEditor, Tag
from dvhaedit.utilities import set_msw_background_color, get_file_paths, get_type, get_selected_listctrl_items,\
    save_csv_to_file, load_csv_from_file, ErrorDialog


VERSION = '0.2'


class MainFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        self.ds = {}

        # Create GUI widgets
        keys =['in_dir', 'tag_group', 'tag_element', 'value', 'out_dir', 'prepend_file_name']
        self.input = {key: wx.TextCtrl(self, wx.ID_ANY, "") for key in keys}
        self.input['selected_file'] = wx.ComboBox(self, wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.input['value_type'] = wx.ComboBox(self, wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.input_obj = [self.input[key] for key in keys]

        keys = ['save_dicom', 'quit', 'in_browse', 'out_browse', 'add', 'delete', 'select_all', 'deselect_all',
                'save_template', 'load_template']
        self.button = {key: wx.Button(self, wx.ID_ANY, key.replace('_', ' ').title()) for key in keys}

        columns = ['Tag', 'Description', 'Value', 'Value Type']
        data = {c: [''] for c in columns}
        self.list_ctrl = wx.ListCtrl(self, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.LC_REPORT)
        self.data_table = DataTable(self.list_ctrl, data=data, columns=columns, widths=[-2] * 4)

        keys = ['tag_group', 'tag_element', 'value', 'value_type', 'files_found', 'description', 'selected_file',
                'modality', 'prepend_file_name']
        self.label = {key: wx.StaticText(self, wx.ID_ANY, key.replace('_', ' ').title() + ':') for key in keys}

        self.file_paths = []
        self.update_files_found()

        self.directory = {'in': '', 'out': ''}
        
        self.__set_properties()
        self.__do_bind()
        self.__do_layout()
    
    def __set_properties(self):
        set_msw_background_color(self)

        self.button['in_browse'].SetLabel(u"Browse…")
        self.button['out_browse'].SetLabel(u"Browse…")
        self.button['save_dicom'].SetLabel('Save DICOM')
        self.button['save_template'].SetLabel('Save')
        self.button['load_template'].SetLabel('Load')

        for key in ['add', 'delete', 'save_dicom', 'save_template']:
            self.button[key].Disable()

        self.input['selected_file'].Disable()
        msg = "The \"Value\" in the tag editor below will be prepopulated with the value found for the " \
              "specified tag in this file."
        self.input['selected_file'].SetToolTip(msg)
        self.label['selected_file'].SetToolTip(msg)

        self.input['value_type'].SetItems(['str', 'float', 'int'])
        self.input['value_type'].SetValue('str')
    
    def __do_bind(self):
        for key, button in self.button.items():
            self.Bind(wx.EVT_BUTTON, getattr(self, "on_" + key), id=button.GetId())

        self.Bind(wx.EVT_COMBOBOX, self.on_file_select, id=self.input['selected_file'].GetId())

        for widget in self.input_obj:
            widget.Bind(wx.EVT_KEY_UP, self.on_key_up)

        self.input['in_dir'].Bind(wx.EVT_KEY_DOWN, self.on_key_down_dir)
        self.input['out_dir'].Bind(wx.EVT_KEY_DOWN, self.on_key_down_dir)

        self.input['in_dir'].Bind(wx.EVT_TEXT, self.update_dir_obj_text_color)
        self.input['out_dir'].Bind(wx.EVT_TEXT, self.update_dir_obj_text_color)

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.update_delete_enable, id=self.list_ctrl.GetId())

    def __do_layout(self):
        # Create GUI sizers
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_input_dir_wrapper = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Directory"), wx.VERTICAL)
        sizer_input_dir = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input_file = wx.BoxSizer(wx.VERTICAL)
        sizer_edit_wrapper = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Tag Editor"), wx.VERTICAL)
        sizer_edit = wx.BoxSizer(wx.HORIZONTAL)
        sizer_edit_widgets = {key: wx.BoxSizer(wx.VERTICAL)
                              for key in ['tag_group', 'tag_element', 'value', 'value_type', 'add']}
        sizer_edit_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_output_dir_wrapper = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Output Directory"), wx.VERTICAL)
        sizer_output_dir = wx.BoxSizer(wx.HORIZONTAL)
        sizer_output_dir_prepend = wx.BoxSizer(wx.HORIZONTAL)
        sizer_app_buttons = wx.BoxSizer(wx.HORIZONTAL)

        # Directory Browser
        sizer_input_dir.Add(self.input['in_dir'], 1, wx.EXPAND | wx.ALL, 5)
        sizer_input_dir.Add(self.button['in_browse'], 0, wx.ALL, 5)
        sizer_input_dir_wrapper.Add(sizer_input_dir, 0, wx.ALL | wx.EXPAND, 5)
        sizer_input_file.Add(self.label['files_found'], 0, wx.ALL, 5)
        sizer_input_file.Add(self.label['selected_file'], 0, wx.LEFT | wx.TOP, 5)
        sizer_input_file.Add(self.input['selected_file'], 0, wx.EXPAND | wx.LEFT | wx.BOTTOM, 5)
        sizer_input_file.Add(self.label['modality'], 0, wx.LEFT, 5)
        sizer_input_dir_wrapper.Add(sizer_input_file, 0, wx.ALL | wx.EXPAND, 5)
        sizer_main.Add(sizer_input_dir_wrapper, 0, wx.EXPAND | wx.ALL, 5)

        # Input Widgets
        for key in ['tag_group', 'tag_element', 'value_type']:
            sizer_edit_widgets[key].Add(self.label[key], 0, 0, 0)
            sizer_edit_widgets[key].Add(self.input[key], 0, wx.EXPAND, 0)
            sizer_edit.Add(sizer_edit_widgets[key], 0, wx.EXPAND | wx.ALL, 5)
        sizer_edit_widgets['add'].Add((5, 13), 0, wx.EXPAND, 0)  # Align Button
        sizer_edit_widgets['add'].Add(self.button['add'], 0, wx.EXPAND, 0)
        sizer_edit.Add(sizer_edit_widgets['add'], 0, wx.EXPAND | wx.ALL, 5)
        sizer_edit_wrapper.Add(sizer_edit, 0, wx.EXPAND | wx.ALL, 5)

        sizer_edit_wrapper.Add(self.label['value'], 0, wx.LEFT, 10)
        sizer_edit_wrapper.Add(self.input['value'], 0, wx.EXPAND | wx.LEFT, 10)

        sizer_edit_wrapper.Add(self.label['description'], 0, wx.TOP | wx.LEFT | wx.BOTTOM, 10)

        sizer_edit_wrapper.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 10)

        for key in ['delete', 'select_all', 'deselect_all', 'save_template', 'load_template']:
            sizer_edit_buttons.Add(self.button[key], 0, wx.EXPAND | wx.RIGHT | wx.LEFT, 5)
        sizer_edit_wrapper.Add(sizer_edit_buttons, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        sizer_main.Add(sizer_edit_wrapper, 1, wx.EXPAND | wx.ALL, 5)

        # Output Directory Browser
        sizer_output_dir.Add(self.input['out_dir'], 1, wx.EXPAND | wx.ALL, 5)
        sizer_output_dir.Add(self.button['out_browse'], 0, wx.ALL, 5)
        sizer_output_dir_wrapper.Add(sizer_output_dir, 0, wx.ALL | wx.EXPAND, 5)
        sizer_output_dir_prepend.Add(self.label['prepend_file_name'], 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sizer_output_dir_prepend.Add(self.input['prepend_file_name'], 1, wx.EXPAND | wx.RIGHT, 110)
        sizer_output_dir_wrapper.Add(sizer_output_dir_prepend, 0, wx.EXPAND | wx.LEFT | wx.BOTTOM, 5)
        sizer_main.Add(sizer_output_dir_wrapper, 0, wx.EXPAND | wx.ALL, 5)

        sizer_app_buttons.Add(self.button['save_dicom'], 0, wx.ALL, 5)
        sizer_app_buttons.Add(self.button['quit'], 0, wx.ALL, 5)
        sizer_main.Add(sizer_app_buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        sizer_wrapper.Add(sizer_main, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer_wrapper)
        self.Fit()
        self.Center()

    def on_key_up(self, evt):
        keycode = evt.GetKeyCode()
        if keycode == wx.WXK_TAB:
            self.on_tab_key(evt)
        evt.Skip()

    def on_tab_key(self, evt):
        obj = evt.GetEventObject()
        index = self.input_obj.index(obj)
        index = index + 1 if index + 1 < len(self.input_obj) else 0
        if obj in {self.input['in_dir'], self.input['out_dir']}:
            new_dir = obj.GetValue()
            if isdir(new_dir):
                if obj == self.input['in_dir'] and new_dir != self.directory['in']:
                    self.refresh_ds()
            else:
                ErrorDialog(self, "Please enter a valid directory.", "Directory Error")
                dir_key = 'in' if obj == self.input['in_dir'] else 'out'
                self.directory[dir_key] = new_dir
                index -= 1
        self.input_obj[index].SetFocus()
        self.update_save_dicom_enable()
        self.update_description()
        if obj == self.input['in_dir']:
            self.update_init_value()

    def get_files(self):
        dir_path = self.input['in_dir'].GetValue()
        if isdir(dir_path):
            self.file_paths = sorted(get_file_paths(dir_path))
        else:
            self.file_paths = []
        self.update_files_found()

    def update_files_found(self):
        found = len(self.file_paths)
        label = "Files Found: %s" % found
        self.label['files_found'].SetLabel(label)
        self.button['add'].Enable(found > 0)

    @property
    def group(self):
        return self.input['tag_group'].GetValue().replace('(', '').replace(')', '').strip()

    @property
    def element(self):
        return self.input['tag_element'].GetValue().replace('(', '').replace(')', '').strip()

    @property
    def tag(self):
        return Tag(self.group, self.element)

    @property
    def value(self):
        value = self.input['value'].GetValue()
        type_ = get_type(self.input['value_type'].GetValue())
        return type_(value)

    def on_save_dicom(self, *evt):
        self.apply_edits()
        if self.save_files(overwrite_check_only=True):
            msg = "You will overwrite files with this action. Continue?"
            caption = "Are you sure?"
            flags = wx.ICON_WARNING | wx.YES | wx.NO | wx.NO_DEFAULT
            with wx.MessageDialog(self, msg, caption, flags) as dlg:
                if dlg.ShowModal() != wx.ID_YES:
                    return
        self.save_files()

        if self.input['in_dir'].GetValue() == self.input['out_dir'].GetValue():
            self.get_files()
            self.refresh_ds()

    def on_quit(self, *evt):
        self.Close()

    def on_in_browse(self, *evt):
        self.on_browse(self.input['in_dir'])

    def on_browse(self, obj):
        starting_dir = obj.GetValue()
        if not isdir(starting_dir):
            starting_dir = ""

        dlg = wx.DirDialog(self, "Select directory", starting_dir, wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            obj.SetBackgroundColour(wx.WHITE)
            new_dir = dlg.GetPath()
            obj.ChangeValue(new_dir)
            if obj == self.input['in_dir']:
                self.refresh_ds()
                self.directory['in'] = new_dir
            else:
                self.directory['out'] = new_dir
            self.input['tag_group'].SetFocus()
        else:
            obj.SetFocus()
        self.update_save_dicom_enable()

    def on_key_down_dir(self, evt):
        keycode = evt.GetKeyCode()
        obj = evt.GetEventObject()
        if keycode == wx.WXK_RETURN:
            self.on_enter_key_dir(obj)
            if obj == self.input['in_dir']:
                self.update_description()
                self.update_init_value()
        else:
            evt.Skip()

    def update_dir_obj_text_color(self, evt):
        obj = evt.GetEventObject()
        orange = (255, 153, 51, 255)
        color = wx.WHITE if isdir(obj.GetValue()) else orange  # else orange
        if color != obj.GetBackgroundColour():
            obj.SetBackgroundColour(color)
            self.update_save_dicom_enable()

    def update_save_dicom_enable(self):
        enable = isdir(self.input['in_dir'].GetValue()) and \
                 isdir(self.input['out_dir'].GetValue()) and \
                 self.data_table_has_data
        self.button['save_dicom'].Enable(enable)

        if self.input['in_dir'].GetValue() == self.input['out_dir'].GetValue() and \
                not self.input['prepend_file_name'].GetValue():
            self.input['prepend_file_name'].ChangeValue('copy_')

    def on_enter_key_dir(self, obj):
        new_dir = obj.GetValue()
        key = 'in' if obj == self.input['in_dir'] else 'out'
        if new_dir == self.directory[key]:
            if isdir(obj.GetValue()):
                if obj == self.input['in_dir']:
                    self.refresh_ds()
            else:
                ErrorDialog(self, "Please enter a valid directory.", "Directory Error")
                dir_key = 'in' if obj == self.input['in_dir'] else 'out'
                self.directory[dir_key] = new_dir

    def refresh_ds(self):
        self.get_files()
        self.ds = {}
        new_file_paths = []
        for f in self.file_paths:
            try:
                self.ds[f] = DICOMEditor(f)
                new_file_paths.append(f)
            except Exception:
                pass
        self.file_paths = new_file_paths
        self.update_combo_box_files()
        self.update_init_value()

    def update_combo_box_files(self):
        choices = [basename(f) for f in self.file_paths]
        self.input['selected_file'].Enable()
        self.input['selected_file'].SetItems(choices)
        if choices:
            self.input['selected_file'].SetValue(choices[0])

    def on_file_select(self, *evt):
        self.update_init_value()

    def update_init_value(self):
        index = self.input['selected_file'].GetSelection()
        if self.group and self.element:
            try:
                value = self.ds[self.file_paths[index]].get_tag_value(self.tag.tag)
                self.input['value'].SetValue(value)
            except Exception:
                self.input['value'].SetValue('')
        self.update_modality(index)

    def update_modality(self, index=None):
        if index is None:
            index = self.input['selected_file'].GetSelection()
        modality = self.ds[self.file_paths[index]].modality if self.file_paths else ''
        self.label['modality'].SetLabel('Modality: ' + modality)

    def on_out_browse(self, *evt):
        self.on_browse(self.input['out_dir'])

    def on_add(self, *evt):
        try:
            description = self.ds[self.file_paths[0]].get_tag_name(self.tag.tag)
        except KeyError:
            description = 'Unknown'
        row = [str(self.tag), description, self.input['value'].GetValue(), self.input['value_type'].GetValue()]
        if self.data_table_has_data:
            self.data_table.append_row(row)
        else:
            columns = self.data_table.columns
            data = {columns[i]: [value] for i, value in enumerate(row)}
            self.data_table.set_data(data, columns)
        self.data_table.set_column_widths(auto=True)

        for key in ['tag_group', 'tag_element', 'value']:
            self.input[key].SetValue('')

        self.input['tag_group'].SetFocus()
        self.update_description()
        self.update_save_template_enable()
        self.update_save_dicom_enable()

    @property
    def data_table_has_data(self):
        return self.data_table.has_data and self.data_table.get_row(0)[0] != ''

    def on_delete(self, *evt):
        for index in self.selected_indices[::-1]:
            self.data_table.delete_row(index)
        self.update_delete_enable()
        self.update_save_template_enable()
        self.update_save_dicom_enable()

    def on_select_all(self, *evt):
        self.data_table.apply_selection_to_all(True)
        self.button['delete'].Enable()

    def on_deselect_all(self, *evt):
        self.data_table.apply_selection_to_all(False)
        self.button['delete'].Disable()

    def on_save_template(self, *evt):
        dlg = wx.FileDialog(self, "Save template", "", wildcard='*.csv',
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            save_csv_to_file(self.data_table.get_csv(), dlg.GetPath())
        dlg.Destroy()

    def on_load_template(self, *evt):
        dlg = wx.FileDialog(self, "Load template", "", wildcard='*.csv', style=wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            columns, data = load_csv_from_file(dlg.GetPath())
            if columns == self.data_table.columns:
                self.data_table.set_data(data, columns)
                self.data_table.set_column_widths(auto=True)
                self.update_save_template_enable()
                self.update_save_dicom_enable()

    def update_delete_enable(self, *evt):
        self.button['delete'].Enable(len(self.data_table.selected_row_data))

    def update_save_template_enable(self):
        self.button['save_template'].Enable(self.data_table_has_data)

    @property
    def selected_indices(self):
        return get_selected_listctrl_items(self.list_ctrl)

    def apply_edits(self):
        for ds in self.ds.values():
            for row in range(self.data_table.row_count):
                row_data = self.data_table.get_row(row)
                group = row_data[0].split(',')[0][1:].strip()
                element = row_data[0].split(',')[1][:-1].strip()
                tag = Tag(group, element).tag

                value_str = row_data[2]
                value_type = get_type(row_data[3])
                value = value_type(value_str)

                try:
                    ds.edit_tag(tag, value)
                except Exception:
                    pass

    def save_files(self, overwrite_check_only=False):
        output_dir = self.input['out_dir'].GetValue()
        prepend = self.input['prepend_file_name'].GetValue()
        for file_path, ds in self.ds.items():
            file_name = prepend + basename(file_path)
            output_path = join(output_dir, file_name)
            if overwrite_check_only:
                if output_path in list(self.ds):
                    return True
            else:
                try:
                    ds.save_as(output_path)
                except OSError as e:
                    ErrorDialog(self, str(e), "Save Error")
                    break

        if overwrite_check_only:
            return False

    def update_description(self):
        description = self.description if self.group and self.element else ''
        self.label['description'].SetLabel("Description: %s" % description)
        self.update_tag_type()

    def update_tag_type(self):
        tag = self.tag.tag
        tag_type = 'str'
        for file_path in self.file_paths:
            try:
                tag_type = self.ds[file_path].get_tag_type(tag)
                break
            except Exception:
                pass
        self.input['value_type'].SetValue(tag_type)

    @property
    def description(self):
        for file_path in self.file_paths:
            try:
                return self.ds[file_path].get_tag_name(self.tag.tag)
            except Exception:
                pass
        return 'Not Found'


class MainApp(wx.App):
    def OnInit(self):

        self.SetAppName('DVHA DICOM Editor')
        self.frame = MainFrame(None, wx.ID_ANY, "DVHA DICOM Editor v%s" % VERSION)
        self.SetTopWindow(self.frame)
        self.frame.Show()
        return True


def start():
    app = MainApp(0)
    app.MainLoop()
