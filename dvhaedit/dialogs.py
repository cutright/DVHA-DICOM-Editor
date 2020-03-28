#!/usr/bin/env python
# -*- coding: utf-8 -*-

# dicom_editor.py
"""
Classes used to edit pydicom datasets
"""
# Copyright (c) 2020 Dan Cutright
# This file is part of DVHA DICOM Editor, released under a BSD license.
#    See the file LICENSE included with this distribution, also
#    available at https://github.com/cutright/DVHA-DICOM-Editor

import wx
from dvhaedit.data_table import DataTable
from dvhaedit.dicom_editor import TagSearch
from dvhaedit.utilities import save_csv_to_file, get_window_size


class ErrorDialog:
    """This class allows error messages to be called with a one-liner else-where"""

    def __init__(self, parent, message, caption, flags=wx.ICON_ERROR | wx.OK | wx.OK_DEFAULT):
        """
        :param parent: wx parent object
        :param message: error message
        :param caption: error title
        :param flags: flags for wx.MessageDialog
        """
        self.dlg = wx.MessageDialog(parent, message, caption, flags)
        self.dlg.Center()
        self.dlg.ShowModal()
        self.dlg.Destroy()


class AskYesNo(wx.MessageDialog):
    """Simple Yes/No MessageDialog"""

    def __init__(self, parent, msg, caption="Are you sure?", flags=wx.ICON_WARNING | wx.YES | wx.NO | wx.NO_DEFAULT):
        wx.MessageDialog.__init__(self, parent, msg, caption, flags)

    @property
    def run(self):
        ans = self.ShowModal() == wx.YES
        self.Destroy()
        return ans


class ViewErrorLog(wx.Dialog):
    """Simple dialog to display the error log in a scrollable window"""

    def __init__(self, error_log):
        wx.Dialog.__init__(self, None, title='Error log')

        self.error_log = error_log

        scrolled_window = wx.ScrolledWindow(self, wx.ID_ANY)

        text = "The following errors occurred while editing DICOM tags...\n\n%s" % error_log

        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_text = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)

        dismiss_button = wx.Button(self, wx.ID_OK, "Dismiss")
        save_button = wx.Button(self, wx.ID_ANY, "Save")
        self.Bind(wx.EVT_BUTTON, self.on_save, id=save_button.GetId())

        scrolled_window.SetScrollRate(20, 20)

        text = wx.StaticText(scrolled_window, wx.ID_ANY, text)
        sizer_text.Add(text, 0, wx.EXPAND | wx.ALL, 5)
        scrolled_window.SetSizer(sizer_text)
        sizer_wrapper.Add(scrolled_window, 1, wx.EXPAND, 0)

        sizer_buttons.Add(save_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer_buttons.Add(dismiss_button, 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer_wrapper.Add(sizer_buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        scrolled_window.SetBackgroundColour(wx.WHITE)

        self.SetSizer(sizer_wrapper)
        self.SetSize(get_window_size(0.4, 0.4))
        self.Center()

        self.ShowModal()
        self.Destroy()

    def on_save(self, *evt):
        dlg = wx.FileDialog(self, "Save error log", "", wildcard='*.txt',
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            save_csv_to_file(self.error_log, dlg.GetPath())
        dlg.Destroy()


class TagSearchDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title='DICOM Tag Search')

        self.parent = parent

        self.search_ctrl = wx.SearchCtrl(self, wx.ID_ANY, "")
        self.search = TagSearch()

        columns = ['Keyword', 'Tag']
        data = {c: [''] for c in columns}
        self.list_ctrl = wx.ListCtrl(self, wx.ID_ANY, style=wx.BORDER_SUNKEN | wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.data_table = DataTable(self.list_ctrl, data=data, columns=columns, widths=[-2, -2])

        keys = {'select': wx.ID_OK, 'cancel': wx.ID_CANCEL}
        self.button = {key: wx.Button(self, id_, key.capitalize()) for key, id_ in keys.items()}

        self.__set_properties()
        self.__do_bind()
        self.__do_layout()

        res = self.ShowModal()
        if res == wx.ID_OK:
            self.set_tag_to_selection()
        self.Destroy()

    def __set_properties(self):
        pass

    def __do_bind(self):
        self.Bind(wx.EVT_TEXT, self.update, id=self.search_ctrl.GetId())

    def __do_layout(self):
        sizer_wrapper = wx.BoxSizer(wx.VERTICAL)
        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_search = wx.BoxSizer(wx.VERTICAL)
        sizer_buttons = wx.BoxSizer(wx.HORIZONTAL)

        sizer_search.Add(self.search_ctrl, 0, wx.EXPAND | wx.ALL, 5)
        sizer_search.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        sizer_main.Add(sizer_search, 1, wx.EXPAND | wx.ALL, 5)

        sizer_buttons.Add(self.button['select'], 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer_buttons.Add(self.button['cancel'], 0, wx.ALIGN_RIGHT | wx.ALL, 5)
        sizer_main.Add(sizer_buttons, 0, wx.ALIGN_RIGHT | wx.ALL, 5)

        sizer_wrapper.Add(sizer_main, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer_wrapper)
        self.SetSize(get_window_size(0.4, 0.4))
        self.Center()

    @property
    def data_dict(self):
        return self.search(self.search_ctrl.GetValue())

    @property
    def selected_tag(self):
        selected_data = self.data_table.selected_row_data
        if selected_data:
            return selected_data[0][1]

    def update(self, *evt):
        self.data_table.set_data(**self.data_dict)

    def set_tag_to_selection(self):
        tag = self.selected_tag
        if tag:
            self.parent.input['tag_group'].SetValue(tag.group)
            self.parent.input['tag_element'].SetValue(tag.element)
