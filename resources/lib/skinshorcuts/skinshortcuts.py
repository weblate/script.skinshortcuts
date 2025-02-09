# -*- coding: utf-8 -*-
"""
    Copyright (C) 2013-2021 Skin Shortcuts (script.skinshortcuts)
    This file is part of script.skinshortcuts
    SPDX-License-Identifier: GPL-2.0-only
    See LICENSES/GPL-2.0-only.txt for more information.
"""

import _thread as thread
import calendar
import os
import sys
from time import gmtime
from time import strftime
from traceback import print_exc
from urllib.parse import parse_qsl
from urllib.parse import unquote

import xbmc
import xbmcgui
import xbmcplugin
import xbmcvfs

from . import datafunctions
from . import library
from . import nodefunctions
from . import xmlfunctions
from .common import log
from .common import rpc_request
from .constants import ADDON_NAME
from .constants import CWD
from .constants import DATA_PATH
from .constants import HOME_WINDOW
from .constants import LANGUAGE
from .constants import MASTER_PATH
from .constants import SKIN_DIR


class Main:
    # MAIN ENTRY POINT
    def __init__(self):
        self._parse_argv()

        self.data_func = datafunctions.DataFunctions()
        self.node_func = nodefunctions.NodeFunctions()
        self.xml_func = xmlfunctions.XMLFunctions()
        self.lib_func = library.LibraryFunctions()

        # Create data and master paths if not exists
        if not xbmcvfs.exists(DATA_PATH):
            xbmcvfs.mkdir(DATA_PATH)
        if not xbmcvfs.exists(MASTER_PATH):
            xbmcvfs.mkdir(MASTER_PATH)

        # Perform action specified by user
        if not self.TYPE:
            line1 = "This addon is for skin developers, and requires skin support"
            xbmcgui.Dialog().ok(ADDON_NAME, line1)

        if self.TYPE == "buildxml":
            xbmc.sleep(100)
            self.xml_func.build_menu(self.MENUID, self.GROUP, self.LEVELS, self.MODE,
                                     self.OPTIONS, self.MINITEMS)

        if self.TYPE == "launch":
            xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False,
                                      listitem=xbmcgui.ListItem())
            self._launch_shortcut()
        if self.TYPE == "launchpvr":
            json_payload = {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "Player.Open",
                "params": {
                    "item": {
                        "channelid": "%s" % self.CHANNEL
                    }
                }
            }
            _ = rpc_request(json_payload)
        if self.TYPE == "manage":
            self._manage_shortcuts(self.GROUP, self.DEFAULTGROUP, self.NOLABELS, self.GROUPNAME)

        if self.TYPE == "hidesubmenu":
            self._hidesubmenu(self.MENUID)
        if self.TYPE == "resetlist":
            self._resetlist(self.MENUID, self.NEXTACTION)

        setstring_strtpl = "Skin.SetString(%s,%s)"
        skinreset_strtpl = "Skin.Reset(%s)"

        if self.TYPE == "shortcuts":
            # We're just going to choose a shortcut, and save its details to the given
            # skin labels

            # Load library shortcuts in thread
            thread.start_new_thread(self.lib_func.load_all_library, ())

            if self.GROUPING is not None:
                selected_shortcut = self.lib_func.select_shortcut(
                    "", grouping=self.GROUPING,
                    custom=self.CUSTOM, show_none=self.NONE
                )
            else:
                selected_shortcut = self.lib_func.select_shortcut("", custom=self.CUSTOM,
                                                                  show_none=self.NONE)

            # Now set the skin strings
            if selected_shortcut is not None and selected_shortcut.getProperty("Path"):
                path = selected_shortcut.getProperty("Path")

                if selected_shortcut.getProperty("chosenPath"):
                    path = selected_shortcut.getProperty("chosenPath")

                if path.startswith("pvr-channel://"):
                    path = "RunScript(script.skinshortcuts,type=launchpvr&channel=%s)" % \
                           path.replace("pvr-channel://", "")
                if self.LABEL is not None and selected_shortcut.getLabel() != "":
                    xbmc.executebuiltin(setstring_strtpl %
                                        (self.LABEL, selected_shortcut.getLabel()))
                if self.ACTION is not None:
                    xbmc.executebuiltin(setstring_strtpl % (self.ACTION, path))
                if self.SHORTCUTTYPE is not None:
                    xbmc.executebuiltin(setstring_strtpl %
                                        (self.SHORTCUTTYPE, selected_shortcut.getLabel2()))
                if self.THUMBNAIL is not None and selected_shortcut.getProperty("icon"):
                    xbmc.executebuiltin(setstring_strtpl %
                                        (self.THUMBNAIL, selected_shortcut.getProperty("icon")))
                if self.THUMBNAIL is not None and selected_shortcut.getProperty("thumbnail"):
                    xbmc.executebuiltin(setstring_strtpl %
                                        (self.THUMBNAIL,
                                         selected_shortcut.getProperty("thumbnail")))
                if self.LIST is not None:
                    xbmc.executebuiltin(setstring_strtpl %
                                        (self.LIST, self.data_func.get_list_property(path)))
            elif selected_shortcut is not None and selected_shortcut.getLabel() == "::NONE::":
                # Clear the skin strings
                if self.LABEL is not None:
                    xbmc.executebuiltin(skinreset_strtpl % self.LABEL)
                if self.ACTION is not None:
                    xbmc.executebuiltin(skinreset_strtpl % self.ACTION)
                if self.SHORTCUTTYPE is not None:
                    xbmc.executebuiltin(skinreset_strtpl % self.SHORTCUTTYPE)
                if self.THUMBNAIL is not None:
                    xbmc.executebuiltin(skinreset_strtpl % self.THUMBNAIL)
                if self.THUMBNAIL is not None:
                    xbmc.executebuiltin(skinreset_strtpl % self.THUMBNAIL)
                if self.LIST is not None:
                    xbmc.executebuiltin(skinreset_strtpl % self.LIST)

        if self.TYPE == "widgets":
            # We're just going to choose a widget, and save its details to the given
            # skin labels

            # Load library shortcuts in thread
            thread.start_new_thread(self.lib_func.load_all_library, ())

            # Check if we should show the custom option (if the relevant widgetPath skin
            # string is provided and isn't empty)
            show_custom = False
            if self.WIDGETPATH and \
                    xbmc.getCondVisibility("!String.IsEmpty(Skin.String(%s))" % self.WIDGETPATH):
                show_custom = True

            if self.GROUPING:
                if self.GROUPING.lower() == "default":
                    selected_shortcut = self.lib_func.select_shortcut("", custom=show_custom,
                                                                      show_none=self.NONE)
                else:
                    selected_shortcut = self.lib_func.select_shortcut(
                        "", grouping=self.GROUPING,
                        custom=show_custom, show_none=self.NONE
                    )
            else:
                selected_shortcut = self.lib_func.select_shortcut(
                    "", grouping="widget",
                    custom=show_custom, show_none=self.NONE
                )

            # Now set the skin strings
            if selected_shortcut is None:
                # The user cancelled
                return

            if selected_shortcut.getProperty("Path") and \
                    selected_shortcut.getProperty("custom") == "true":
                # The user updated the path - so we just set that property
                xbmc.executebuiltin(
                    "Skin.SetString(%s,%s)" %
                    (self.WIDGETPATH, unquote(selected_shortcut.getProperty("Path")))
                )

            elif selected_shortcut.getProperty("Path"):
                # The user selected the widget they wanted
                if self.WIDGET:
                    if selected_shortcut.getProperty("widget"):
                        xbmc.executebuiltin("Skin.SetString(%s,%s)" %
                                            (self.WIDGET, selected_shortcut.getProperty("widget")))
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % self.WIDGET)
                if self.WIDGETTYPE:
                    if selected_shortcut.getProperty("widgetType"):
                        xbmc.executebuiltin(
                            "Skin.SetString(%s,%s)" %
                            (self.WIDGETTYPE, selected_shortcut.getProperty("widgetType"))
                        )
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % self.WIDGETTYPE)
                if self.WIDGETNAME:
                    if selected_shortcut.getProperty("widgetName"):
                        xbmc.executebuiltin(
                            "Skin.SetString(%s,%s)" %
                            (self.WIDGETNAME, selected_shortcut.getProperty("widgetName"))
                        )
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % self.WIDGETNAME)
                if self.WIDGETTARGET:
                    if selected_shortcut.getProperty("widgetTarget"):
                        xbmc.executebuiltin(
                            "Skin.SetString(%s,%s)" %
                            (self.WIDGETTARGET, selected_shortcut.getProperty("widgetTarget"))
                        )
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % self.WIDGETTARGET)
                if self.WIDGETPATH:
                    if selected_shortcut.getProperty("widgetPath"):
                        xbmc.executebuiltin(
                            "Skin.SetString(%s,%s)" %
                            (self.WIDGETPATH, unquote(selected_shortcut.getProperty("widgetPath")))
                        )
                    else:
                        xbmc.executebuiltin("Skin.Reset(%s)" % self.WIDGETPATH)

            elif selected_shortcut.getLabel() == "::NONE::":
                # Clear the skin strings
                if self.WIDGET is not None:
                    xbmc.executebuiltin(skinreset_strtpl % self.WIDGET)
                if self.WIDGETTYPE is not None:
                    xbmc.executebuiltin(skinreset_strtpl % self.WIDGETTYPE)
                if self.WIDGETNAME is not None:
                    xbmc.executebuiltin(skinreset_strtpl % self.WIDGETNAME)
                if self.WIDGETTARGET is not None:
                    xbmc.executebuiltin(skinreset_strtpl % self.WIDGETTARGET)
                if self.WIDGETPATH is not None:
                    xbmc.executebuiltin(skinreset_strtpl % self.WIDGETPATH)

        if self.TYPE == "context":
            # Context menu addon asking us to add a folder to the menu
            if not xbmc.getCondVisibility("Skin.HasSetting(SkinShortcuts-FullMenu)"):
                xbmcgui.Dialog().ok(ADDON_NAME, LANGUAGE(32116))
            else:
                self.node_func.add_to_menu(self.CONTEXTFILENAME, self.CONTEXTLABEL,
                                           self.CONTEXTICON, self.CONTEXTCONTENT,
                                           self.CONTEXTWINDOW, self.data_func)

        if self.TYPE == "setProperty":
            # External request to set properties of a menu item
            self.node_func.set_properties(self.PROPERTIES, self.VALUES, self.LABELID,
                                          self.GROUPNAME, self.data_func)

        if self.TYPE == "resetall":
            # Tell XBMC not to try playing any media
            try:
                xbmcplugin.setResolvedUrl(handle=int(sys.argv[1]), succeeded=False,
                                          listitem=xbmcgui.ListItem())
            except:
                log("Not launched from a list item")
            self._reset_all_shortcuts()

    # pylint: disable=invalid-name
    def _parse_argv(self):
        params = {}
        try:
            params = dict(parse_qsl(sys.argv[1]))
        except:
            try:
                params = dict(parse_qsl(sys.argv[2].lstrip('?')))
            except:
                pass

        self.TYPE = params.get("type", "")
        self.GROUP = params.get("group", "")
        self.GROUPNAME = params.get("groupname", None)
        self.GROUPING = params.get("grouping", None)
        self.PATH = params.get("path", "")
        self.MENUID = params.get("mainmenuID", "0")
        self.NEXTACTION = params.get("action", "0")
        self.LEVELS = params.get("levels", "0")
        self.MODE = params.get("mode", None)
        self.CHANNEL = params.get("channel", None)

        # Properties when using LIBRARY._displayShortcuts
        self.LABEL = params.get("skinLabel", None)
        self.ACTION = params.get("skinAction", None)
        self.SHORTCUTTYPE = params.get("skinType", None)
        self.THUMBNAIL = params.get("skinThumbnail", None)
        self.LIST = params.get("skinList", None)
        self.CUSTOM = params.get("custom", "False")
        self.NONE = params.get("showNone", "False")

        self.WIDGET = params.get("skinWidget", None)
        self.WIDGETTYPE = params.get("skinWidgetType", None)
        self.WIDGETNAME = params.get("skinWidgetName", None)
        self.WIDGETTARGET = params.get("skinWidgetTarget", None)
        self.WIDGETPATH = params.get("skinWidgetPath", None)

        if self.CUSTOM == "True" or self.CUSTOM == "true":
            self.CUSTOM = True
        else:
            self.CUSTOM = False
        if self.NONE == "True" or self.NONE == "true":
            self.NONE = True
        else:
            self.NONE = False

        self.NOLABELS = params.get("nolabels", "false").lower()
        self.OPTIONS = params.get("options", "").split("|")
        self.MINITEMS = int(params.get("minitems", "0"))
        self.WARNING = params.get("warning", None)
        self.DEFAULTGROUP = params.get("defaultGroup", None)

        # Properties from context menu addon
        self.CONTEXTFILENAME = unquote(params.get("filename", ""))
        self.CONTEXTLABEL = params.get("label", "")
        self.CONTEXTICON = params.get("icon", "")
        self.CONTEXTCONTENT = params.get("content", "")
        self.CONTEXTWINDOW = params.get("window", "")

        # Properties from external request to set properties
        self.PROPERTIES = unquote(params.get("property", ""))
        self.VALUES = unquote(params.get("value", ""))
        self.LABELID = params.get("labelID", "")

    # -----------------
    # PRIMARY FUNCTIONS
    # -----------------

    def _launch_shortcut(self):
        action = unquote(self.PATH)

        if action.find("::MULTIPLE::") == -1:
            # Single action, run it
            xbmc.executebuiltin(action)
        else:
            # Multiple actions, separated by |
            actions = action.split("|")
            for single_action in actions:
                if single_action != "::MULTIPLE::":
                    xbmc.executebuiltin(single_action)

    @staticmethod
    def _manage_shortcuts(group, default_group, nolabels, groupname):
        if HOME_WINDOW.getProperty("skinshortcuts-loading") and \
                int(calendar.timegm(gmtime())) - \
                int(HOME_WINDOW.getProperty("skinshortcuts-loading")) <= 5:
            return

        HOME_WINDOW.setProperty("skinshortcuts-loading", str(calendar.timegm(gmtime())))
        from . import gui  # pylint: disable=import-outside-toplevel
        dialog = gui.GUI("script-skinshortcuts.xml", CWD, "default", group=group,
                         default_group=default_group, nolabels=nolabels, groupname=groupname)
        dialog.doModal()
        del dialog

        # Update home window property (used to automatically refresh type=settings)
        HOME_WINDOW.setProperty("skinshortcuts", strftime("%Y%m%d%H%M%S", gmtime()))

        # Clear window properties for this group, and for backgrounds, widgets, properties
        HOME_WINDOW.clearProperty("skinshortcuts-%s" % group)
        HOME_WINDOW.clearProperty("skinshortcutsWidgets")
        HOME_WINDOW.clearProperty("skinshortcutsCustomProperties")
        HOME_WINDOW.clearProperty("skinshortcutsBackgrounds")

    def _reset_all_shortcuts(self):
        log("Resetting all shortcuts")
        dialog = xbmcgui.Dialog()

        should_run = None
        if self.WARNING is not None and self.WARNING.lower() == "false":
            should_run = True

        # Ask the user if they're sure they want to do this
        if should_run is None:
            should_run = dialog.yesno(LANGUAGE(32037), LANGUAGE(32038))

        if should_run:
            is_shared = self.data_func.check_if_menus_shared()
            for files in xbmcvfs.listdir(DATA_PATH):
                # Try deleting all shortcuts
                if files:
                    for file in files:
                        delete_file = False
                        if file == "settings.xml":
                            continue
                        if is_shared:
                            delete_file = True
                        elif file.startswith(SKIN_DIR) and \
                                (file.endswith(".properties") or file.endswith(".DATA.xml")):
                            delete_file = True

                        # if file != "settings.xml" and ( not isShared or
                        # file.startswith( "%s-" %( xbmc.getSkinDir() ) ) ) or
                        # file == "%s.properties" %( xbmc.getSkinDir() ):
                        if delete_file:
                            file_path = os.path.join(DATA_PATH, file)
                            if xbmcvfs.exists(file_path):
                                try:
                                    xbmcvfs.delete(file_path)
                                except:
                                    log(print_exc())
                                    log("Could not delete file %s" % file)
                        else:
                            log("Not deleting file %s" % file)

            # Update home window property (used to automatically refresh type=settings)
            HOME_WINDOW.setProperty("skinshortcuts", strftime("%Y%m%d%H%M%S", gmtime()))

    # Functions for providing whole menu in single list
    @staticmethod
    def _hidesubmenu(menuid):
        count = 0
        while xbmc.getCondVisibility(
                "!String.IsEmpty(Container(%s).ListItem(%i).Property(isSubmenu))" % (menuid, count)
        ):
            count -= 1

        if count != 0:
            xbmc.executebuiltin("Control.Move(%s,%s)" % (menuid, str(count)))

        xbmc.executebuiltin("ClearProperty(submenuVisibility, 10000)")

    @staticmethod
    def _resetlist(menuid, action):
        count = 0
        while xbmc.getCondVisibility(
                "!String.IsEmpty(Container(%s).ListItemNoWrap(%i).Label)" % (menuid, count)
        ):
            count -= 1

        count += 1

        if count != 0:
            xbmc.executebuiltin("Control.Move(%s,%s)" % (menuid, str(count)))

        xbmc.executebuiltin(unquote(action))
