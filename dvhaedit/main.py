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
from copy import deepcopy
from os import sep
from os.path import isdir, isfile, basename, join, dirname, normpath, splitext, relpath
from pathlib import Path
from pubsub import pub
from pydicom.datadict import keyword_dict
import webbrowser
from dvhaedit.data_table import DataTable
from dvhaedit.dialogs import ErrorDialog, ViewErrorLog, AskYesNo, TagSearchDialog, About,ParsingProgressFrame,\
    SavingProgressFrame, DynamicValueHelp, AdvancedSettings, RefSyncProgressFrame, ValueGenProgressFrame,\
    ApplyEditsProgressFrame
from dvhaedit.dicom_editor import Tag
from dvhaedit.dynamic_value import ValueGenerator
from dvhaedit.options import Options
from dvhaedit.utilities import set_msw_background_color, get_file_paths, get_type, get_selected_listctrl_items,\
    get_window_size, is_mac, save_object_to_file, load_object_from_file, set_frame_icon


VERSION = '0.4'


class MainFrame(wx.Frame):
    """The main frame called in MainApp"""
    def __init__(self, *args, **kwds):
        kwds["style"] = kwds.get("style", 0) | wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)

        self.ds = {}
        self.functions = ValueGenerator().functions
        self.all_options = {}
        self.current_options = Options()
        self.value_generators = []
        self.values_dicts = []

        self.error_log = ''
        self.history = []

        # Create GUI widgets
        keys = ['in_dir', 'tag_group', 'tag_element', 'value', 'out_dir', 'prepend_file_name']
        self.input = {key: wx.TextCtrl(self, wx.ID_ANY, "") for key in keys}
        self.input['preview'] = wx.TextCtrl(self, wx.ID_ANY, "", style=wx.TE_READONLY)
        self.input['selected_file'] = wx.ComboBox(self, wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.input['value_type'] = wx.ComboBox(self, wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY)
        self.input_text_obj = [self.input[key] for key in keys]  # use for text event binding and focusing

        keys = ['save_dicom', 'quit', 'in_browse', 'out_browse', 'add', 'delete', 'select_all', 'deselect_all',
                'save_template', 'load_template', 'advanced']
        self.button = {key: wx.Button(self, wx.ID_ANY, key.replace('_', ' ').title()) for key in keys}
        bmp = wx.ArtProvider.GetBitmap(wx.ART_FIND, size=(16, 16))
        self.button['search'] = wx.BitmapButton(self, id=wx.ID_ANY, bitmap=bmp)
        bmp = wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, size=(16, 16))
        self.button['value_help'] = wx.BitmapButton(self, id=wx.ID_ANY, bitmap=bmp)

        columns = ['Index', 'Tag', 'Keyword', 'Value', 'Value Type']
        data = {c: [''] for c in columns}
        self.list_ctrl = wx.ListCtrl(self, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.LC_REPORT)
        self.data_table = DataTable(self.list_ctrl, data=data, columns=columns, widths=[-2] * 5)

        keys = ['tag_group', 'tag_element', 'value', 'value_type', 'files_found', 'keyword', 'selected_file',
                'modality', 'prepend_file_name', 'search', 'value_rep', 'preview', 'advanced', 'value_help']
        self.label = {key: wx.StaticText(self, wx.ID_ANY, key.replace('_', ' ').title() + ':') for key in keys}

        self.search_sub_folders = wx.CheckBox(self, wx.ID_ANY, "Search Sub-Folders")
        self.search_sub_folders_last_status = False

        self.retain_rel_dir = wx.CheckBox(self, wx.ID_ANY, "Retain relative directory structure")

        self.referenced_tag_choices = ['Only Edit Tags Defined in Table',
                                       'Update "Referenced" Tags',
                                       'Update All Tags with Matching UID']
        self.update_referenced_tags = wx.ComboBox(self, wx.ID_ANY, style=wx.CB_DROPDOWN | wx.CB_READONLY,
                                                  choices=self.referenced_tag_choices)

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

        for checkbox in [self.search_sub_folders, self.retain_rel_dir]:
            checkbox.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, 0, ""))
        self.retain_rel_dir.SetToolTip("If unchecked, all new files will be placed in the output directory. "
                                       "Otherwise, the same relative directory structure will be used.")
        self.retain_rel_dir.SetValue(True)

        self.button['in_browse'].SetLabel(u"Browse…")
        self.button['out_browse'].SetLabel(u"Browse…")
        self.button['save_dicom'].SetLabel('Save DICOM')
        self.button['save_template'].SetLabel('Save')
        self.button['load_template'].SetLabel('Load')

        self.label['advanced'].SetLabel(' ')
        self.label['search'].SetLabel(' ')
        self.label['value_help'].SetLabel(' ')
        self.label['value_rep'].SetLabel('Value Representation (VR): ')
        self.label['value'].SetLabel('Enter New DICOM Tag Value Here: ')

        self.button['search'].SetToolTip("Search for DICOM tag based on keyword.")
        self.input['preview'].SetToolTip("Values may be set dynamically, a preview is shown here. Note that generated "
                                         "UIDs may be different than the final value if no entropy source is "
                                         "provided.")
        if is_mac():
            self.input['preview'].SetBackgroundColour((230, 230, 230))

        for key in ['add', 'delete', 'save_dicom', 'save_template', 'advanced']:
            self.button[key].Disable()

        self.input['selected_file'].Disable()
        msg = "The \"Value\" in the tag editor below will be prepopulated with the value found for the " \
              "specified tag in this file."
        self.input['selected_file'].SetToolTip(msg)
        self.label['selected_file'].SetToolTip(msg)

        self.input['value_type'].SetItems(['str', 'float', 'int'])
        self.input['value_type'].SetValue('str')

        self.update_referenced_tags.SetValue(self.referenced_tag_choices[1])
        self.update_referenced_tags.SetToolTip("Automatically sync Referenced<tag> to new <tag> value to maintain "
                                               "cross-file connections (e.g., keep RT-Structure connection to "
                                               "RT-Plan). If this doesn't work, try Update All Tags with Matching UID "
                                               "(much slower).")

    def __add_menubar(self):

        self.frame_menubar = wx.MenuBar()

        file_menu = wx.Menu()
        menu_open = file_menu.Append(wx.ID_OPEN, '&Open\tCtrl+O')
        self.menu_save = file_menu.Append(wx.ID_ANY, '&Save\tCtrl+S')
        self.menu_save.Enable(False)
        file_menu.Append(wx.ID_SEPARATOR)
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
        file_menu.Append(wx.ID_SEPARATOR)
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
        pub.subscribe(self.on_save_complete, 'save_complete')
        pub.subscribe(self.do_saving_progress_frame, 'ref_sync_complete')
        pub.subscribe(self.add_value_dicts, 'add_value_dicts')
        pub.subscribe(self.call_next_value_generator, 'value_gen_complete')
        pub.subscribe(self.update_dicom_edits, 'update_dicom_edits')
        pub.subscribe(self.do_save_dicom, 'do_save_dicom')

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
                              for key in ['tag_group', 'tag_element', 'value', 'value_type', 'value_help',
                                          'add', 'search', 'advanced']}
        sizer_value_keyword = wx.BoxSizer(wx.VERTICAL)
        sizer_edit_buttons = wx.BoxSizer(wx.HORIZONTAL)
        sizer_output_dir_wrapper = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Output Directory"), wx.HORIZONTAL)
        sizer_output_dir_inner_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_output_dir = wx.BoxSizer(wx.VERTICAL)
        sizer_output_dir_prepend = wx.BoxSizer(wx.HORIZONTAL)
        sizer_app_buttons = wx.BoxSizer(wx.HORIZONTAL)

        # Directory Browser
        sizer_input_dir.Add(self.input['in_dir'], 1, wx.EXPAND | wx.ALL, 5)
        sizer_input_dir.Add(self.button['in_browse'], 0, wx.ALL, 5)
        sizer_input_dir_wrapper.Add(sizer_input_dir, 0, wx.ALL | wx.EXPAND, 5)
        row_sizer = wx.BoxSizer(wx.HORIZONTAL)
        row_sizer.Add(self.label['files_found'], 1, wx.EXPAND, 0)
        row_sizer.Add(self.search_sub_folders, 0, wx.ALIGN_RIGHT, 0)
        sizer_input_file.Add(row_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        sizer_input_file.Add(self.label['selected_file'], 0, wx.LEFT | wx.TOP, 5)
        sizer_input_file.Add(self.input['selected_file'], 0, wx.EXPAND | wx.LEFT | wx.BOTTOM, 5)
        sizer_input_file.Add(self.label['modality'], 0, wx.LEFT, 5)
        sizer_input_dir_wrapper.Add(sizer_input_file, 0, wx.ALL | wx.EXPAND, 5)
        sizer_main.Add(sizer_input_dir_wrapper, 0, wx.EXPAND | wx.ALL, 5)

        # Input Widgets
        for key in ['search', 'tag_group', 'tag_element', 'value_type', 'value_help', 'advanced']:
            obj = self.button if key in {'search', 'value_help', 'advanced'} else self.input
            sizer_edit_widgets[key].Add(self.label[key], 0, wx.EXPAND, 0)
            sizer_edit_widgets[key].Add(obj[key], 0, wx.EXPAND, 0)
            proportion = 'tag' in key
            sizer_edit.Add(sizer_edit_widgets[key], proportion, wx.EXPAND | wx.ALL, 5)
        sizer_edit_wrapper.Add(sizer_edit, 0, wx.EXPAND | wx.ALL, 5)

        sizer_value_keyword.Add(self.label['value'], 0, wx.LEFT, 5)
        row_sizer_value_help = wx.BoxSizer(wx.HORIZONTAL)
        row_sizer_value_help.Add(self.input['value'], 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        row_sizer_value_help.Add(self.button['add'], 0, wx.LEFT | wx.RIGHT, 5)
        sizer_value_keyword.Add(row_sizer_value_help, 1, wx.EXPAND, 5)
        sizer_value_keyword.Add(self.label['keyword'], 0, wx.TOP | wx.LEFT, 5)
        sizer_value_keyword.Add(self.label['value_rep'], 0, wx.LEFT | wx.BOTTOM, 5)
        sizer_value_keyword.Add(self.label['preview'], 0, wx.BOTTOM | wx.LEFT, 5)
        sizer_value_keyword.Add(self.input['preview'], 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)
        sizer_edit_wrapper.Add(sizer_value_keyword, 0, wx.EXPAND | wx.ALL, 5)

        sizer_edit_wrapper.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 10)
        for key in ['delete', 'select_all', 'deselect_all', 'save_template', 'load_template']:
            sizer_edit_buttons.Add(self.button[key], 0, wx.EXPAND | wx.RIGHT | wx.LEFT, 5)
        sizer_edit_wrapper.Add(sizer_edit_buttons, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        sizer_main.Add(sizer_edit_wrapper, 1, wx.EXPAND | wx.ALL, 5)

        # Output Directory Browser
        sizer_output_dir.Add(self.input['out_dir'], 1, wx.EXPAND | wx.ALL, 5)
        sizer_output_dir.Add(self.retain_rel_dir, 0, wx.LEFT | wx.BOTTOM, 5)
        sizer_output_dir_inner_wrapper.Add(sizer_output_dir, 0, wx.ALL | wx.EXPAND, 5)
        sizer_output_dir_prepend.Add(self.label['prepend_file_name'], 0, wx.TOP | wx.LEFT | wx.RIGHT, 5)
        sizer_output_dir_prepend.Add(self.input['prepend_file_name'], 1, wx.EXPAND | wx.RIGHT, 5)
        sizer_output_dir_inner_wrapper.Add(sizer_output_dir_prepend, 0, wx.EXPAND | wx.LEFT | wx.BOTTOM | wx.RIGHT, 5)
        sizer_output_dir_wrapper.Add(sizer_output_dir_inner_wrapper, 1, wx.EXPAND, 5)
        sizer_output_dir_wrapper.Add(self.button['out_browse'], 0, wx.ALIGN_TOP | wx.TOP, 10)
        sizer_main.Add(sizer_output_dir_wrapper, 0, wx.EXPAND | wx.ALL, 5)

        sizer_app_buttons.Add(self.update_referenced_tags, 0, wx.ALIGN_LEFT | wx.ALL, 5)
        sizer_app_buttons.Add((20, 20), 1, wx.EXPAND | wx.ALIGN_LEFT | wx.ALL, 5)
        sizer_app_buttons.Add(self.button['save_dicom'], 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer_app_buttons.Add(self.button['quit'], 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer_main.Add(sizer_app_buttons, 0, wx.EXPAND | wx.ALL, 5)

        sizer_wrapper.Add(sizer_main, 1, wx.EXPAND | wx.ALL, 5)

        self.SetMinSize(get_window_size(0.35, 0.8))
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
    def keyword(self):
        return self.tag.keyword

    @property
    def selected_indices(self):
        return get_selected_listctrl_items(self.list_ctrl)

    @property
    def selected_file(self):
        return self.input['selected_file'].GetSelection()

    @property
    def selected_data_set(self):
        return self.ds.get(self.file_paths[self.selected_file])

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
            else:
                self.directory['out'] = new_dir
            self.input['tag_group'].SetFocus()
        else:
            obj.SetFocus()
        self.update_save_dicom_enable()

    def on_add(self, *evt):
        """Add a tag edit"""
        keys_int = [int(key) for key in list(self.all_options)]
        row_index = '0' if not keys_int else str(max(keys_int) + 1)
        self.all_options[row_index] = deepcopy(self.current_options)
        row = [row_index,
               str(self.tag),
               self.keyword,
               self.input['value'].GetValue(),
               self.input['value_type'].GetValue()]
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
        self.update_keyword()
        self.update_save_template_enable()
        self.update_save_dicom_enable()

    def on_link(self, *evt):
        self.selected_data_set.find_tag(self.tag.tag)

    def on_search(self, *evt):
        TagSearchDialog(self)

    def on_value_help(self, *evt):
        DynamicValueHelp()

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
            tag = selected_data[0][1][1:-1].split(',')
            group = tag[0].strip()
            element = tag[1].strip()
            self.input['tag_group'].SetValue(group)
            self.input['tag_element'].SetValue(element)
            self.input['value_type'].SetValue(selected_data[0][4])
            self.update_keyword()
            self.update_init_value()
            self.update_preview()
            self.current_options = deepcopy(self.all_options[selected_data[0][0]])

    def on_save_template(self, *evt):
        """Save the current tag edits to a pickle file"""
        dlg = wx.FileDialog(self, "Save template", "", wildcard='*.pickle',
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            save_data = {'table': self.data_table.get_save_data(), 'options': self.all_options}
            save_object_to_file(save_data, dlg.GetPath())
        dlg.Destroy()

    def on_load_template(self, *evt):
        """Load a pickle file of tag edits"""
        dlg = wx.FileDialog(self, "Load template", "", wildcard='*.pickle', style=wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            try:
                loaded_data = load_object_from_file(dlg.GetPath())
                self.data_table.load_save_data(loaded_data['table'])
                self.all_options = loaded_data['options']
            except Exception:
                self.data_table.clear()

        self.update_save_template_enable()
        self.update_save_dicom_enable()

    def on_save_dicom(self, *evt):
        """Apply edits, check for errors, then run save_files"""
        if self.dir_contents_have_changed:
            with AskYesNo(self, "Directory contents have changed. Continue anyway?") as dlg:
                if dlg.ShowModal() == wx.ID_NO:
                    return

        # Can be expensive, on_save_dicom, split to enable threading
        # calls do_save_dicom when done
        self.calculate_value_generators()

    def apply_edits(self):
        all_row_data = [self.get_table_row_data(row) for row in range(self.data_table.row_count)]
        ApplyEditsProgressFrame(self.ds, self.values_dicts, all_row_data)

    def update_dicom_edits(self, msg):
        self.history = msg['data']['history']
        self.error_log = msg['data']['error_log']
        self.ds = msg['data']['ds']

    def do_save_dicom(self):
        if self.error_log:
            ViewErrorLog(self.error_log)
            with AskYesNo(self, "Ignore errors and write DICOM files anyway?") as dlg:
                if dlg.ShowModal() == wx.ID_NO:
                    return

        if self.set_output_paths(check_only=True):
            msg = "You will overwrite files with this action. Continue?"
            caption = "Are you sure?"
            flags = wx.ICON_WARNING | wx.YES | wx.NO | wx.NO_DEFAULT
            with wx.MessageDialog(self, msg, caption, flags) as dlg:
                if dlg.ShowModal() == wx.ID_NO:
                    return
        self.set_output_paths()

        if self.update_referenced_tags.GetSelection() and self.a_referenced_tag_exists(self.history):
            check_all_tags = True if self.update_referenced_tags.GetSelection() == 2 else False
            RefSyncProgressFrame(self.history, self.ds.values(), check_all_tags)
            # This will call SavingProgressFrame when done
        else:
            self.do_saving_progress_frame()

    @staticmethod
    def a_referenced_tag_exists(history):
        return any(["Referenced%s" % row[0] in list(keyword_dict) for row in history])

    def do_saving_progress_frame(self):
        SavingProgressFrame(self.ds.values())

    def on_save_complete(self):
        # If in and out directories are the same, need to update file list and datasets with new files
        if self.input['in_dir'].GetValue() == self.input['out_dir'].GetValue():
            self.get_files()
            wx.CallAfter(self.refresh_ds)

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
            self.update_keyword()
        evt.Skip()

    def on_tab_key(self, evt):
        obj = evt.GetEventObject()
        index = self.input_text_obj.index(obj)
        index = index + 1 if index + 1 < len(self.input_text_obj) else 0
        if obj in {self.input['in_dir'], self.input['out_dir']}:
            new_dir = obj.GetValue()
            if isdir(new_dir):
                if obj == self.input['in_dir']:
                    self.refresh_ds()
            else:
                ErrorDialog(self, "Please enter a valid directory.", "Directory Error")
                dir_key = 'in' if obj == self.input['in_dir'] else 'out'
                self.directory[dir_key] = new_dir
                if obj == self.input['in_dir']:
                    self.file_paths = []
                    self.ds = {}
                    self.on_parse_complete()
                index -= 1
        self.input_text_obj[index].SetFocus()
        self.update_save_dicom_enable()
        self.update_keyword()
        if obj == self.input['in_dir']:
            self.update_init_value()

    def on_key_down_dir(self, evt):
        """Called on any key down in directory TextCtrl, only act on Enter/Return"""
        keycode = evt.GetKeyCode()
        obj = evt.GetEventObject()
        if keycode == wx.WXK_RETURN:
            self.on_enter_key_dir(obj)
            if obj == self.input['in_dir']:
                self.update_keyword()
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
        if isdir(new_dir):
            if obj == self.input['in_dir']:
                self.refresh_ds()
        else:
            ErrorDialog(self, "Please enter a valid directory.", "Directory Error")
            dir_key = 'in' if obj == self.input['in_dir'] else 'out'
            self.directory[dir_key] = new_dir
            if obj == self.input['in_dir']:
                self.file_paths = []
                self.ds = {}
                self.on_parse_complete()

    #################################################################################
    # Combobox Event tickers
    #################################################################################
    def on_file_select(self, *evt):
        self.update_modality()
        self.update_init_value()

    #################################################################################
    # Text Event tickers
    #################################################################################
    def update_dir_obj_text_color(self, evt):
        """Set directory TextCtrl background to orange if directory is invalid"""
        obj = evt.GetEventObject()
        orange = (255, 153, 51, 255)
        color = wx.WHITE if isdir(obj.GetValue()) else orange
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

    def update_add_enable(self, *evt):
        enable = len(self.file_paths) > 0 and bool(self.group) and bool(self.element) and self.value_is_valid
        self.button['add'].Enable(enable)
        value_str = self.input['value'].GetValue()
        adv_enable = enable and any([v in value_str for v in ['*fuid[', '*vuid', '*frand[', '*vrand']])
        self.button['advanced'].Enable(adv_enable)
        if enable:
            self.update_preview()
        else:
            self.input['preview'].SetValue('')
        self.update_keyword()

    def update_combobox_files(self):
        """Update the combobox with the file names found in the current in directory"""
        choices = [relpath(f, self.directory['in']) for f in self.file_paths]
        self.input['selected_file'].Enable()
        self.input['selected_file'].SetItems(choices)
        if choices:
            self.input['selected_file'].SetValue(choices[0])

    def update_init_value(self):
        """Update Value in the Tag Editor based on the currently selected file"""
        if self.ds and self.group and self.element:
            ds = self.ds[self.file_paths[self.selected_file]]
            try:
                value = str(ds.get_tag_value(self.tag.tag))
            except Exception:
                try:
                    address = ds.find_tag(self.tag.tag)[0]
                    value = str(address[-1][1])
                except Exception:
                    value = ''
            self.input['value'].SetValue(value)

    def update_modality(self):
        """Update Modality in the Directory box based on the currently selected file"""
        modality = self.ds[self.file_paths[self.selected_file]].modality if self.file_paths else ''
        self.label['modality'].SetLabel('Modality: ' + modality)

    def update_keyword(self):
        """Update Keyword in the Tag Editor based on the current Tag and currently selected file"""
        keyword = self.keyword if self.group and self.element else ''
        self.label['keyword'].SetLabel("Keyword: %s" % keyword)
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
        value = self.tag.vr if self.group and self.element else ''
        self.label['value_rep'].SetLabel("Value Representation (VR): %s" % value)

    def update_preview(self):
        """Apply the tag edits to every file in self.ds, return any errors"""
        # TODO: auto-update Value Type based on VR
        # TODO: validate New Value against Value Type
        tag = self.tag
        value_str = self.value
        value_gen = ValueGenerator(value_str, tag.tag, self.current_options)
        file = self.file_paths[self.selected_file]
        value = value_gen(self.ds, file_path=file) if file in self.ds.keys() else ''
        self.input['preview'].SetValue(value)

    #################################################################################
    # Data updaters
    #################################################################################
    def get_files(self):
        """Get a list of all files in the currently specified in directory"""
        dir_path = self.input['in_dir'].GetValue()
        self.directory['in'] = dir_path
        if isdir(dir_path):
            self.search_sub_folders_last_status = self.search_sub_folders.GetValue()
            self.file_paths = sorted(get_file_paths(dir_path, search_sub_folders=self.search_sub_folders.GetValue()))
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
        value_functions = [f for f in self.functions if f[0] == 'v']
        for call in call_str:
            if '[' not in call and ']' not in call:
                if call not in value_functions:
                    return False
            else:
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
        current_files = sorted(get_file_paths(self.directory['in'],
                                              search_sub_folders=self.search_sub_folders_last_status))
        return current_files != self.file_paths

    def add_parsed_data(self, msg):
        self.ds[msg['obj']] = msg['data']

    def on_advanced(self, *evt):
        AdvancedSettings(self.current_options)
        self.update_preview()

    #################################################################################
    # Finally... run the DICOM editor and save DICOM files
    #################################################################################
    def calculate_value_generators(self):
        """Apply the tag edits to every file in self.ds, return any errors"""
        self.value_generators = []
        for row in range(self.data_table.row_count):
            row_data = self.get_table_row_data(row)
            self.value_generators.append(ValueGenerator(row_data['value_str'],
                                                        row_data['tag'].tag,
                                                        row_data['options']))
        wx.CallAfter(self.call_next_value_generator)

    def call_next_value_generator(self):
        if self.value_generators:
            value_generator = self.value_generators.pop(0)
            iteration = self.data_table.row_count - len(self.value_generators)
            ValueGenProgressFrame(self.ds, value_generator, iteration, self.data_table.row_count)
        else:
            wx.CallAfter(self.apply_edits)

    def add_value_dicts(self, msg):
        self.values_dicts.append(msg['data'])

    def get_table_row_data(self, row):
        row_data = self.data_table.get_row(row)
        group = row_data[1].split(',')[0][1:].strip()
        element = row_data[1].split(',')[1][:-1].strip()
        return {'tag': Tag(group, element),
                'keyword': row_data[2],
                'value_str': row_data[3],
                'value_type': get_type(row_data[4]),
                'options': self.all_options[row_data[0]]}

    def set_output_paths(self, check_only=False):
        """
        Save all of the loaded pydicom datasets with the new edits
        :param check_only: If true, perform loop without save to check for overwriting
        :type check_only: bool
        :return: status of file overwriting, if overwrite_check_only=True
        :rtype: bool
        """
        output_dir = self.input['out_dir'].GetValue()
        input_dir = self.directory['in']
        prepend = self.input['prepend_file_name'].GetValue()
        for file_path, ds in self.ds.items():
            file_name = prepend + basename(file_path)
            output_path = join(output_dir, file_name)
            if self.retain_rel_dir.GetValue():
                rel_out_path = join(output_dir, relpath(dirname(file_path), input_dir))
                if not check_only:
                    Path(rel_out_path).mkdir(parents=True, exist_ok=True)
                output_path = join(rel_out_path, file_name)

            if check_only:
                if isfile(output_path):
                    return True
            else:
                ds.output_path = output_path

        if check_only:
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
        set_frame_icon(self.frame)
        self.SetTopWindow(self.frame)
        self.frame.Show()
        return True


def start():
    app = MainApp(0)
    app.MainLoop()
