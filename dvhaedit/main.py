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
from os import sep
from os.path import isdir, basename, join, dirname, normpath, splitext
from pubsub import pub
import webbrowser
from dvhaedit.data_table import DataTable
from dvhaedit.dialogs import ErrorDialog, ViewErrorLog, AskYesNo, TagSearchDialog, About, ParsingProgressFrame
from dvhaedit.dicom_editor import Tag
from dvhaedit.dynamic_value import ValueGenerator
from dvhaedit.utilities import set_msw_background_color, get_file_paths, get_type, get_selected_listctrl_items,\
    save_csv_to_file, load_csv_from_file


VERSION = '0.3dev1'


class MainFrame(wx.Frame):
    """The main frame called in MainApp"""
    def __init__(self, *args, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        self.ds = {}
        self.functions = ValueGenerator().functions

        # Create GUI widgets
        keys =['in_dir', 'tag_group', 'tag_element', 'value', 'out_dir', 'prepend_file_name']
        self.input = {key: wx.TextCtrl(self, wx.ID_ANY, "") for key in keys}
        self.input['selected_file'] = wx.ComboBox(self, wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.input['value_type'] = wx.ComboBox(self, wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.input_text_obj = [self.input[key] for key in keys]  # use for text event binding and focusing

        keys = ['save_dicom', 'quit', 'in_browse', 'out_browse', 'add', 'delete', 'select_all', 'deselect_all',
                'save_template', 'load_template']
        self.button = {key: wx.Button(self, wx.ID_ANY, key.replace('_', ' ').title()) for key in keys}
        bmp = wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, size=(16, 16))
        self.button['search'] = wx.BitmapButton(self, id=wx.ID_ANY, bitmap=bmp)

        columns = ['Tag', 'Description', 'Value', 'Value Type']
        data = {c: [''] for c in columns}
        self.list_ctrl = wx.ListCtrl(self, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.LC_REPORT)
        self.data_table = DataTable(self.list_ctrl, data=data, columns=columns, widths=[-2] * 4)

        keys = ['tag_group', 'tag_element', 'value', 'value_type', 'files_found', 'description', 'selected_file',
                'modality', 'prepend_file_name', 'add', 'search', 'value_rep']
        self.label = {key: wx.StaticText(self, wx.ID_ANY, key.replace('_', ' ').title() + ':') for key in keys}

        self.file_paths = []
        self.update_files_found()
        self.refresh_needed = False

        self.directory = {'in': '', 'out': ''}
        
        self.__set_properties()
        self.__add_menubar()
        self.__do_subscribe()
        self.__do_bind()
        self.__do_layout()
    
    def __set_properties(self):
        """Set initial properties of widgets"""
        set_msw_background_color(self)

        self.button['in_browse'].SetLabel(u"Browse…")
        self.button['out_browse'].SetLabel(u"Browse…")
        self.button['save_dicom'].SetLabel('Save DICOM')
        self.button['save_template'].SetLabel('Save')
        self.button['load_template'].SetLabel('Load')

        self.label['add'].SetLabel(' ')
        self.label['search'].SetLabel(' ')
        self.label['value_rep'].SetLabel('Value Representation (VR): ')

        self.button['search'].SetToolTip("Search for DICOM tag based on keyword.")

        self.label['description'].SetToolTip("If a description is not found, then the current tag could not be found "
                                             "in any of the loaded DICOM Files or it is within a sequence "
                                             "(not yet supported).")

        for key in ['add', 'delete', 'save_dicom', 'save_template']:
            self.button[key].Disable()

        self.input['selected_file'].Disable()
        msg = "The \"Value\" in the tag editor below will be prepopulated with the value found for the " \
              "specified tag in this file."
        self.input['selected_file'].SetToolTip(msg)
        self.label['selected_file'].SetToolTip(msg)

        self.input['value_type'].SetItems(['str', 'float', 'int'])
        self.input['value_type'].SetValue('str')

    def __add_menubar(self):

        self.frame_menubar = wx.MenuBar()

        file_menu = wx.Menu()
        menu_open = file_menu.Append(wx.ID_OPEN, '&Open\tCtrl+O')
        self.menu_save = file_menu.Append(wx.ID_ANY, '&Save\tCtrl+S')
        self.menu_save.Enable(False)

        qmi = file_menu.Append(wx.ID_ANY, '&Quit\tCtrl+Q')

        help_menu = wx.Menu()
        menu_github = help_menu.Append(wx.ID_ANY, 'GitHub Page')
        menu_report_issue = help_menu.Append(wx.ID_ANY, 'Report an Issue')
        menu_about = help_menu.Append(wx.ID_ANY, '&About')

        self.Bind(wx.EVT_MENU, self.on_quit, qmi)
        self.Bind(wx.EVT_MENU, self.on_load_template, menu_open)
        self.Bind(wx.EVT_MENU, self.on_save_template, self.menu_save)
        self.Bind(wx.EVT_MENU, self.on_githubpage, menu_github)
        self.Bind(wx.EVT_MENU, self.on_report_issue, menu_report_issue)
        self.Bind(wx.EVT_MENU, self.on_about, menu_about)

        self.frame_menubar.Append(file_menu, '&File')
        self.frame_menubar.Append(help_menu, '&Help')
        self.SetMenuBar(self.frame_menubar)
    
    def __do_bind(self):
        """Bind user events to widgets with actions"""

        # This requires that there is a function on_<button-key> for every button, simplifies bind
        for key, button in self.button.items():
            self.Bind(wx.EVT_BUTTON, getattr(self, "on_" + key), id=button.GetId())

        self.Bind(wx.EVT_COMBOBOX, self.on_file_select, id=self.input['selected_file'].GetId())

        for widget in self.input_text_obj:
            widget.Bind(wx.EVT_KEY_UP, self.on_key_up)

        for key in ['in_dir', 'out_dir']:
            self.input[key].Bind(wx.EVT_KEY_DOWN, self.on_key_down_dir)
            self.input[key].Bind(wx.EVT_TEXT, self.update_dir_obj_text_color)

        self.input['value'].Bind(wx.EVT_TEXT, self.update_add_enable)

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_selection, id=self.list_ctrl.GetId())

    def __do_subscribe(self):
        pub.subscribe(self.add_parsed_data, "add_parsed_data")
        pub.subscribe(self.on_parse_complete, "parse_complete")

    def on_parse_complete(self):
        self.update_combobox_files()
        self.update_init_value()
        self.update_modality()

    def __do_layout(self):
        """Create GUI layout"""
        # Create GUI sizers
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_input_dir_wrapper = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Directory"), wx.VERTICAL)
        sizer_input_dir = wx.BoxSizer(wx.HORIZONTAL)
        sizer_input_file = wx.BoxSizer(wx.VERTICAL)
        sizer_edit_wrapper = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Tag Editor"), wx.VERTICAL)
        sizer_edit = wx.BoxSizer(wx.HORIZONTAL)
        sizer_edit_widgets = {key: wx.BoxSizer(wx.VERTICAL)
                              for key in ['tag_group', 'tag_element', 'value', 'value_type', 'add', 'search']}
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
        for key in ['search', 'tag_group', 'tag_element', 'value_type', 'add']:
            obj = self.button if key in {'search', 'add'} else self.input
            sizer_edit_widgets[key].Add(self.label[key], 0, 0, 0)
            sizer_edit_widgets[key].Add(obj[key], 0, wx.EXPAND, 0)
            sizer_edit.Add(sizer_edit_widgets[key], 0, wx.EXPAND | wx.ALL, 5)
        sizer_edit_wrapper.Add(sizer_edit, 0, wx.EXPAND | wx.ALL, 5)

        sizer_edit_wrapper.Add(self.label['value'], 0, wx.LEFT, 10)
        sizer_edit_wrapper.Add(self.input['value'], 0, wx.EXPAND | wx.LEFT, 10)
        sizer_edit_wrapper.Add(self.label['description'], 0, wx.TOP | wx.LEFT, 10)
        sizer_edit_wrapper.Add(self.label['value_rep'], 0, wx.LEFT | wx.BOTTOM, 10)

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

    #################################################################################
    # Basic properties/getters
    #################################################################################
    @property
    def group(self):
        """Group of the DICOM tag"""
        return self.input['tag_group'].GetValue()

    @property
    def element(self):
        """Element of the DICOM tag"""
        return self.input['tag_element'].GetValue()

    @property
    def tag(self):
        """
        Convert string input in GUI to a DICOM tag
        :return: user provided tag
        :rtype: Tag
        """
        return Tag(self.group, self.element)

    @property
    def value(self):
        value = self.input['value'].GetValue()
        type_ = get_type(self.input['value_type'].GetValue())
        return type_(value)

    @property
    def description(self):
        for file_path in self.file_paths:
            try:
                return self.ds[file_path].get_tag_name(self.tag.tag)
            except Exception:
                pass
        return 'Not Found'

    @property
    def selected_indices(self):
        return get_selected_listctrl_items(self.list_ctrl)

    @property
    def selected_file(self):
        return self.input['selected_file'].GetSelection()

    @property
    def data_table_has_data(self):
        return self.data_table.has_data and self.data_table.get_row(0)[0] != ''

    #################################################################################
    # Button Event tickers
    #################################################################################
    def on_in_browse(self, *evt):
        self.on_browse(self.input['in_dir'])
        if self.refresh_needed:
            self.refresh_ds()
            self.refresh_needed = False

    def on_out_browse(self, *evt):
        self.on_browse(self.input['out_dir'])

    def on_browse(self, obj):
        """
        Open a wx.DirDialog and select a new directory the provided obj
        :param obj: either in_dir or out_dir TextCtrl objects
        :type obj: wx.TextCtrl
        """
        starting_dir = obj.GetValue()
        if not isdir(starting_dir):
            starting_dir = ""

        dlg = wx.DirDialog(self, "Select directory", starting_dir, wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            new_dir = dlg.GetPath()
            dlg.Destroy()
            obj.SetBackgroundColour(wx.WHITE)  # Reset if background was orange, DirDialog forces a valid directory
            obj.ChangeValue(new_dir)  # Update TextCtrl without signaling a change event
            if obj == self.input['in_dir']:
                self.refresh_needed = True
                self.directory['in'] = new_dir
            else:
                self.directory['out'] = new_dir
            self.input['tag_group'].SetFocus()
        else:
            obj.SetFocus()
        self.update_save_dicom_enable()

    def on_add(self, *evt):
        """Add a tag edit"""
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

    def on_search(self, *evt):
        TagSearchDialog(self)

    def on_delete(self, *evt):
        """Delecte the selected tag edits"""
        for index in self.selected_indices[::-1]:
            self.data_table.delete_row(index)
        self.update_delete_enable()
        self.update_save_template_enable()
        self.update_save_dicom_enable()

    def on_select_all(self, *evt):
        """Select all tag edits"""
        self.data_table.apply_selection_to_all(True)
        self.button['delete'].Enable()

    def on_deselect_all(self, *evt):
        """Deselect all tag edits"""
        self.data_table.apply_selection_to_all(False)
        self.button['delete'].Disable()

    def on_selection(self, *evt):
        self.update_delete_enable()
        selected_data = self.data_table.selected_row_data
        if selected_data:
            tag = selected_data[0][0][1:-1].split(',')
            group = tag[0].strip()
            element = tag[1].strip()
            self.input['tag_group'].SetValue(group)
            self.input['tag_element'].SetValue(element)
            self.input['value_type'].SetValue(selected_data[0][3])

    def on_save_template(self, *evt):
        """Save the current tag edits to a CSV"""
        dlg = wx.FileDialog(self, "Save template", "", wildcard='*.csv',
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            save_csv_to_file(self.data_table.get_csv(), dlg.GetPath())
        dlg.Destroy()

    def on_load_template(self, *evt):
        """Load a CSV of tag edits"""
        dlg = wx.FileDialog(self, "Load template", "", wildcard='*.csv', style=wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            columns, data = load_csv_from_file(dlg.GetPath())
            if columns == self.data_table.columns:
                self.data_table.set_data(data, columns)
                self.data_table.set_column_widths(auto=True)
                self.update_save_template_enable()
                self.update_save_dicom_enable()

    def on_save_dicom(self, *evt):
        """Apply edits, check for errors, then run save_files"""
        if self.dir_contents_have_changed:
            if not AskYesNo(self, "Directory contents have changed. Continue anyway?").run:
                return

        error_log = self.apply_edits()  # Edits the loaded pydicom datasets
        if error_log:
            ViewErrorLog(error_log)
            if not AskYesNo(self, "Continue writing DICOM files anyway?").run:
                return

        if self.save_files(overwrite_check_only=True):
            msg = "You will overwrite files with this action. Continue?"
            caption = "Are you sure?"
            flags = wx.ICON_WARNING | wx.YES | wx.NO | wx.NO_DEFAULT
            with wx.MessageDialog(self, msg, caption, flags) as dlg:
                if dlg.ShowModal() != wx.ID_YES:
                    return
        self.save_files()

        # If in and out directories are the same, need to update file list and datasets with new files
        if self.input['in_dir'].GetValue() == self.input['out_dir'].GetValue():
            self.get_files()
            self.refresh_ds()

    def on_quit(self, *evt):
        self.Close()

    #################################################################################
    # Key Event tickers
    #################################################################################
    def on_key_up(self, evt):
        """Called anytime a user's key is released"""
        keycode = evt.GetKeyCode()
        if keycode == wx.WXK_TAB:
            self.on_tab_key(evt)
        elif evt.GetEventObject() in {self.input['tag_group'], self.input['tag_element']}:
            self.update_description()
        evt.Skip()

    def on_tab_key(self, evt):
        obj = evt.GetEventObject()
        index = self.input_text_obj.index(obj)
        index = index + 1 if index + 1 < len(self.input_text_obj) else 0
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
        self.input_text_obj[index].SetFocus()
        self.update_save_dicom_enable()
        self.update_description()
        if obj == self.input['in_dir']:
            self.update_init_value()

    def on_key_down_dir(self, evt):
        """Called on any key down in directory TextCtrl, only act on Enter/Return"""
        keycode = evt.GetKeyCode()
        obj = evt.GetEventObject()
        if keycode == wx.WXK_RETURN:
            self.on_enter_key_dir(obj)
            if obj == self.input['in_dir']:
                self.update_description()
                self.update_init_value()
        else:
            evt.Skip()

    def on_enter_key_dir(self, obj):
        """
        Similar to on_browse, except need to check for valid directory
        :param obj: either in_dir or out_dir TextCtrl objects
        :type obj: wx.TextCtrl
        """
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

    #################################################################################
    # Combobox Event tickers
    #################################################################################
    def on_file_select(self, *evt):
        self.update_init_value()

    #################################################################################
    # Text Event tickers
    #################################################################################
    def update_dir_obj_text_color(self, evt):
        """Set directory TextCtrl background to orange if directory is invalid"""
        obj = evt.GetEventObject()
        orange = (255, 153, 51, 255)
        color = wx.WHITE if isdir(obj.GetValue()) else orange  # else orange
        if color != obj.GetBackgroundColour():
            obj.SetBackgroundColour(color)
            self.update_save_dicom_enable()

    #################################################################################
    # Widget Enabling
    #################################################################################
    def update_save_dicom_enable(self):
        """Disable save dicom button if there is not enough information provided"""
        enable = isdir(self.input['in_dir'].GetValue()) and \
                 isdir(self.input['out_dir'].GetValue()) and \
                 self.data_table_has_data
        self.button['save_dicom'].Enable(enable)

        if self.input['in_dir'].GetValue() == self.input['out_dir'].GetValue() and \
                not self.input['prepend_file_name'].GetValue():
            self.input['prepend_file_name'].ChangeValue('copy_')

    def update_delete_enable(self, *evt):
        """Only enable delete button if edits in the ListCtrl are selected"""
        self.button['delete'].Enable(len(self.data_table.selected_row_data))

    def update_save_template_enable(self):
        """Only enable save button if the ListCtrl has data"""
        enable = self.data_table_has_data
        self.button['save_template'].Enable(enable)
        self.menu_save.Enable(enable)

    #################################################################################
    # Widget updaters
    #################################################################################
    def update_files_found(self):
        """Update the number of files in the GUI"""
        found = len(self.file_paths)
        label = "Files Found: %s" % found
        self.label['files_found'].SetLabel(label)
        self.update_add_enable()
        self.button['search'].Enable(found > 0)

    def update_add_enable(self, *evt):
        enable = len(self.file_paths) > 0 and bool(self.group) and bool(self.element) and self.value_is_valid
        self.button['add'].Enable(enable)

    def update_combobox_files(self):
        """Update the combobox with the file names found in the current in directory"""
        choices = [basename(f) for f in self.file_paths]
        self.input['selected_file'].Enable()
        self.input['selected_file'].SetItems(choices)
        if choices:
            self.input['selected_file'].SetValue(choices[0])

    def update_init_value(self):
        """Update Value in the Tag Editor based on the currently selected file"""
        if self.group and self.element:
            try:
                value = self.ds[self.file_paths[self.selected_file]].get_tag_value(self.tag.tag)
                self.input['value'].SetValue(value)
            except Exception:
                self.input['value'].SetValue('')

    def update_modality(self):
        """Update Modality in the Directory box based on the currently selected file"""
        modality = self.ds[self.file_paths[self.selected_file]].modality if self.file_paths else ''
        self.label['modality'].SetLabel('Modality: ' + modality)

    def update_description(self):
        """Update Description in the Tag Editor based on the current Tag and currently selected file"""
        description = self.description if self.group and self.element else ''
        self.label['description'].SetLabel("Description: %s" % description)
        self.update_tag_type()
        self.update_vr()

    def update_tag_type(self):
        """Update tag type in the Tag Editor based on the current Tag and currently selected file"""
        tag = self.tag.tag
        tag_type = 'str'
        for file_path in self.file_paths:
            try:
                tag_type = self.ds[file_path].get_tag_type(tag)
                break
            except Exception:
                pass
        self.input['value_type'].SetValue(tag_type)

    def update_vr(self):
        self.label['value_rep'].SetLabel("Value Representation (VR): %s" % self.tag.vr)

    #################################################################################
    # Data updaters
    #################################################################################
    def get_files(self):
        """Get a list of all files in the currently specified in directory"""
        dir_path = self.input['in_dir'].GetValue()
        if isdir(dir_path):
            self.file_paths = sorted(get_file_paths(dir_path))
        else:
            self.file_paths = []
        self.update_files_found()

    def refresh_ds(self):
        """Update the stored DICOMEditor objects in self.ds"""
        self.get_files()
        self.ds = {}
        ParsingProgressFrame(self.file_paths)

    #################################################################################
    # Utilities
    #################################################################################
    @property
    def value_is_valid(self):
        value = self.input['value'].GetValue()
        if '*' not in value:  # no functions
            return True
        if value.count('*') % 2 == 1:  # has functions, but missing *
            return False

        call_str = value.split('*')[1::2]

        # each call requires left and right square brackets, an int between them, and a valid function call
        for call in call_str:
            if not (call.count('[') == 1 and call.count(']') == 1 and call.endswith(']')):
                return False
            if call.split('[')[0] not in self.functions:
                return False
            param = call.split('[')[1][:-1]
            if not(param.isdigit() or (param.startswith('-') and param[1:].isdigit())):
                return False

        return True

    @staticmethod
    def path_index(value, n):
        if '*dir[' in value and ']' in value:
            value_split = value.split('*')
            index_temp = value_split[n*2 + 1].split('dir[')[1]
            index_temp_end = index_temp.index(']')
            try:
                return index_temp[:index_temp_end]
            except TypeError:
                pass

    def get_nth_dir_from_file_path(self, value, n, file_path):
        index = self.path_index(value, n)
        if index is not None:
            components = normpath(file_path).split(sep)
            if index < len(components):
                return splitext(components[index])[0], index

    @property
    def dir_contents_have_changed(self):
        return sorted(get_file_paths(self.directory['in'])) != self.file_paths

    def add_parsed_data(self, msg):
        self.ds[msg['obj']] = msg['data']

    #################################################################################
    # Finally... run the DICOM editor and save DICOM files
    #################################################################################
    def apply_edits(self):
        """Apply the tag edits to every file in self.ds, return any errors"""
        error_log = []
        for row in range(self.data_table.row_count):

            row_data = self.data_table.get_row(row)
            group = row_data[0].split(',')[0][1:].strip()
            element = row_data[0].split(',')[1][:-1].strip()
            tag = Tag(group, element)

            value_str = row_data[2]
            value_type = get_type(row_data[3])
            value_gen = ValueGenerator(value_str, tag.tag)
            values_dict = value_gen(self.ds)

            for file_path, ds in self.ds.items():

                try:
                    value = value_type(values_dict[file_path])
                    ds.edit_tag(tag.tag, value)
                except Exception as e:
                    err_msg = 'KeyError: %s is not accessible' % tag if str(e).upper() == str(tag).upper() else e
                    value = value_str if value_str else '[empty value]'
                    error_log.append("Directory: %s\nFile: %s\n\tAttempt to edit %s to new value: %s\n\t%s\n" %
                                     (dirname(file_path), basename(file_path), tag, value, err_msg))

        return '\n'.join(error_log)

    def save_files(self, overwrite_check_only=False):
        """
        Save all of the loaded pydicom datasets with the new edits
        :param overwrite_check_only: If true, perform loop without save to check for overwriting
        :type overwrite_check_only: bool
        :return: status of file overwriting, if overwrite_check_only=True
        :rtype: bool
        """
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

    @staticmethod
    def on_about(*evt):
        About(VERSION)

    @staticmethod
    def on_githubpage(evt):
        webbrowser.open_new_tab("https://github.com/cutright/DVHA-DICOM-Editor")

    @staticmethod
    def on_report_issue(evt):
        webbrowser.open_new_tab("https://github.com/cutright/DVHA-DICOM-Editor/issues")


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
