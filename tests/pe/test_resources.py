#!/usr/bin/env python
# -*- coding: utf-8 -*-

import lief
import unittest
import logging
import tempfile
import shutil
import os
import sys
import stat
import subprocess
import time
import ctypes
import zipfile

from subprocess import Popen

from unittest import TestCase
from utils import get_sample

class TestResource(TestCase):
    def setUp(self):
        self.logger = logging.getLogger(__name__)
        self.tmp_dir = tempfile.mkdtemp(suffix='_lief_test_resource')
        self.logger.debug("temp dir: {}".format(self.tmp_dir))


    def test_change_icons(self):
        mfc_path = get_sample('PE/PE64_x86-64_binary_mfc-application.exe')
        mfc = lief.parse(mfc_path)
        mfc_resources_manger = mfc.resources_manager

        cmd_path = get_sample('PE/PE64_x86-64_binary_cmd.exe')
        cmd = lief.parse(cmd_path)
        cmd_resources_manger = cmd.resources_manager

        if not mfc_resources_manger.has_icons:
            print("'{}' has no manifest. Abort!".format(mfc.name))
            sys.exit(1)

        if not cmd_resources_manger.has_icons:
            print("'{}' has no manifest. Abort!".format(mfc.name))
            sys.exit(1)

        mfc_icons = mfc_resources_manger.icons
        cmd_icons = cmd_resources_manger.icons

        for i in range(min(len(mfc_icons), len(cmd_icons))):
            mfc_resources_manger.change_icon(mfc_icons[i], cmd_icons[i])


        output = os.path.join(self.tmp_dir, "mfc_test_change_icon.exe")
        builder = lief.PE.Builder(mfc)
        builder.build_resources(True)
        builder.build()
        builder.write(output)

        if sys.platform.startswith("win"):
            subprocess_flags = 0x8000000 # win32con.CREATE_NO_WINDOW?
            p = Popen(["START", output], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess_flags)
            time.sleep(3)
            q = Popen(["taskkill", "/im", "mfc_test_change_icon.exe"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            stdout, _ = p.communicate()
            self.logger.debug(stdout.decode("utf8"))

            stdout, _ = q.communicate()
            self.logger.debug(stdout.decode("utf8"))

            self.assertEqual(q.returncode, 0)


    def test_resource_string_table(self):
        sample_path = get_sample('PE/PE64_x86-64_binary_WinApp.exe')
        mfc = lief.parse(sample_path)
        resources_manager = mfc.resources_manager

        self.assertEqual(resources_manager.has_string_table, True)

        string_table = resources_manager.string_table
        self.assertEqual(string_table[0].name, "WinApp")
        self.assertEqual(string_table[0].length, 6)

        self.assertEqual(string_table[1].name, "WINAPP")
        self.assertEqual(string_table[1].length, 6)

    def test_resource_accelerator(self):
        sample_path = get_sample('PE/PE64_x86-64_binary_mfc-application.exe')
        mfc = lief.parse(sample_path)
        resources_manager = mfc.resources_manager

        self.assertEqual(resources_manager.has_accelerator, True)

        accelerator = resources_manager.accelerator
        self.assertEqual(accelerator[0].flags, lief.PE.ACCELERATOR_FLAGS.FVIRTKEY | lief.PE.ACCELERATOR_FLAGS.FCONTROL)
        self.assertEqual(accelerator[0].ansi, int(lief.PE.ACCELERATOR_VK_CODES.VK_N))
        self.assertEqual(accelerator[0].id, 0xe100)
        self.assertEqual(accelerator[0].padding, 0)

        self.assertEqual(accelerator[1].flags, lief.PE.ACCELERATOR_FLAGS.FVIRTKEY | lief.PE.ACCELERATOR_FLAGS.FCONTROL)
        self.assertEqual(accelerator[1].ansi, int(lief.PE.ACCELERATOR_VK_CODES.VK_O))
        self.assertEqual(accelerator[1].id, 0xe101)
        self.assertEqual(accelerator[1].padding, 0)

        self.assertEqual(accelerator[2].flags, lief.PE.ACCELERATOR_FLAGS.FVIRTKEY | lief.PE.ACCELERATOR_FLAGS.FCONTROL)
        self.assertEqual(accelerator[2].ansi, int(lief.PE.ACCELERATOR_VK_CODES.VK_S))
        self.assertEqual(accelerator[2].id, 0xe103)
        self.assertEqual(accelerator[2].padding, 0)

    def test_resource_version(self):
        sample_path = get_sample('PE/PE64_x86-64_binary_mfc-application.exe')
        mfc = lief.parse(sample_path)
        resources_manger = mfc.resources_manager

        self.assertEqual(resources_manger.has_version, True)
        version = resources_manger.version

        self.assertEqual(version.type, 0)
        self.assertEqual(version.key, 'VS_VERSION_INFO')

        self.assertEqual(version.has_string_file_info, True)
        self.assertEqual(version.has_var_file_info,    True)
        self.assertEqual(version.has_fixed_file_info,  True)

        fixed_file_info  = version.fixed_file_info
        string_file_info = version.string_file_info
        var_file_info    = version.var_file_info

        # Check ResourceFixedFileInfo
        self.assertEqual(fixed_file_info.signature, 0xFEEF04BD)
        self.assertEqual(fixed_file_info.struct_version, 0x10000)
        self.assertEqual(fixed_file_info.file_version_MS, 0x010000)
        self.assertEqual(fixed_file_info.file_version_LS, 0x000001)
        self.assertEqual(fixed_file_info.product_version_MS, 0x010000)
        self.assertEqual(fixed_file_info.product_version_LS, 0x000001)
        self.assertEqual(fixed_file_info.file_flags_mask, 63)
        self.assertEqual(fixed_file_info.file_flags, 0)
        self.assertEqual(fixed_file_info.file_os, lief.PE.FIXED_VERSION_OS.NT_WINDOWS32)
        self.assertEqual(fixed_file_info.file_type, lief.PE.FIXED_VERSION_FILE_TYPES.APP)
        self.assertEqual(fixed_file_info.file_subtype, lief.PE.FIXED_VERSION_FILE_SUB_TYPES.UNKNOWN)
        self.assertEqual(fixed_file_info.file_date_MS, 0)
        self.assertEqual(fixed_file_info.file_date_LS, 0)

        # Check ResourceStringFileInfo
        self.assertEqual(string_file_info.type, 1)
        self.assertEqual(string_file_info.key, "StringFileInfo")
        self.assertEqual(len(string_file_info.langcode_items), 1)

        langcode_item = string_file_info.langcode_items[0]
        self.assertEqual(langcode_item.type, 1)
        self.assertEqual(langcode_item.lang, lief.PE.RESOURCE_LANGS.FRENCH)
        self.assertEqual(langcode_item.sublang, lief.PE.RESOURCE_SUBLANGS.FRENCH)
        self.assertEqual(langcode_item.code_page, lief.PE.CODE_PAGES.UTF_16)
        items = langcode_item.items
        self.assertIn('CompanyName', items)
        if sys.version_info < (3,):
            self.assertEqual(items['CompanyName'].encode("utf8"), 'TODO: <Nom de la société>')
        else:
            self.assertEqual(items['CompanyName'], b'TODO: <Nom de la soci\xc3\xa9t\xc3\xa9>')

        self.assertIn('FileVersion', items)
        self.assertEqual(items['FileVersion'], b'1.0.0.1')

        self.assertIn('InternalName', items)
        self.assertEqual(items['InternalName'], b'Hello.exe')

        self.assertIn('LegalCopyright', items)
        if sys.version_info < (3,):
            self.assertEqual(items['LegalCopyright'].encode("utf8"), 'TODO: (c) <Nom de la société>.  Tous droits réservés.')
        else:
            self.assertEqual(items['LegalCopyright'].decode("utf8"), 'TODO: (c) <Nom de la société>.  Tous droits réservés.')

        self.assertIn('OriginalFilename', items)
        self.assertEqual(items['OriginalFilename'], b'Hello.exe')

        self.assertIn('ProductName', items)
        self.assertEqual(items['ProductName'], b'TODO: <Nom du produit>')

        self.assertIn('ProductVersion', items)
        self.assertEqual(items['ProductVersion'], b'1.0.0.1')

        # Check ResourceVarFileInfo
        self.assertEqual(var_file_info.type, 1)
        self.assertEqual(var_file_info.key, "VarFileInfo")
        self.assertEqual(len(var_file_info.translations), 1)
        self.assertEqual(var_file_info.translations[0], 0x4b0040c)


    def test_mfc_resource_builder(self):
        sample_path = get_sample('PE/PE64_x86-64_binary_mfc-application.exe')
        output      = os.path.join(self.tmp_dir, "mfc_test_rsrc.exe")

        mfc = lief.parse(sample_path)

        builder = lief.PE.Builder(mfc)
        builder.build_resources(True)
        builder.build()
        builder.write(output)

        st = os.stat(output)
        os.chmod(output, st.st_mode | stat.S_IEXEC)

        if sys.platform.startswith("win"):
            subprocess_flags = 0x8000000 # win32con.CREATE_NO_WINDOW?
            p = Popen(["START", output], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess_flags)
            time.sleep(3)
            q = Popen(["taskkill", "/im", "mfc_test_rsrc.exe"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            stdout, _ = p.communicate()
            self.logger.debug(stdout.decode("utf8"))

            stdout, _ = q.communicate()
            self.logger.debug(stdout.decode("utf8"))

            self.assertEqual(q.returncode, 0)


    #def test_evince_resource_builder(self):
    #    sample_file = get_sample('PE/PE32_x86_binary_EvincePortable.zip')
    #    sample_dir  = os.path.join(self.tmp_dir, "EvincePortable")

    #    sample = os.path.join(sample_dir, "EvincePortable.exe")
    #    output = os.path.join(sample_dir, "evince_rsrc.exe")

    #    zip_ref = zipfile.ZipFile(sample_file, 'r')
    #    zip_ref.extractall(self.tmp_dir)
    #    zip_ref.close()

    #    evince = lief.parse(sample)

    #    builder = lief.PE.Builder(evince)
    #    builder.build_resources(True)
    #    builder.build()
    #    builder.write(output)

    #    st = os.stat(output)
    #    os.chmod(output, st.st_mode | stat.S_IEXEC)

    #    if sys.platform.startswith("win"):
    #        subprocess_flags = 0x8000000 # win32con.CREATE_NO_WINDOW?
    #        p = Popen(["START", output], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess_flags)
    #        time.sleep(3)
    #        q = Popen(["taskkill", "/im", "evince_rsrc.exe"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    #        stdout, _ = p.communicate()
    #        self.logger.debug(stdout.decode("utf8"))

    #        stdout, _ = q.communicate()
    #        self.logger.debug(stdout.decode("utf8"))

    #        self.assertEqual(q.returncode, 0)

    def test_notepadpp_resource_builder(self):
        sample_file = get_sample('PE/PE32_x86_binary_Notepad++.zip')
        sample_dir  = os.path.join(self.tmp_dir, "Notepad++")

        sample = os.path.join(sample_dir, "notepad++.exe")
        output = os.path.join(sample_dir, "notepad++_rsrc.exe")

        zip_ref = zipfile.ZipFile(sample_file, 'r')
        zip_ref.extractall(self.tmp_dir)
        zip_ref.close()

        notepadpp = lief.parse(sample)

        builder = lief.PE.Builder(notepadpp)
        builder.build_resources(True)
        builder.build()
        builder.write(output)

        st = os.stat(output)
        os.chmod(output, st.st_mode | stat.S_IEXEC)

        if sys.platform.startswith("win"):
            subprocess_flags = 0x8000000 # win32con.CREATE_NO_WINDOW?
            p = Popen(["START", output], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess_flags)
            time.sleep(3)
            q = Popen(["taskkill", "/im", "notepad++_rsrc.exe"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            stdout, _ = p.communicate()
            self.logger.debug(stdout.decode("utf8"))

            stdout, _ = q.communicate()
            self.logger.debug(stdout.decode("utf8"))

            self.assertEqual(q.returncode, 0)


    def test_filezilla_resource_builder(self):
        sample_file = get_sample('PE/PE64_x86-64_binary_FileZilla.zip')
        sample_dir  = os.path.join(self.tmp_dir, "FileZilla")

        sample = os.path.join(sample_dir, "filezilla.exe")
        output = os.path.join(sample_dir, "filezilla_rsrc.exe")

        zip_ref = zipfile.ZipFile(sample_file, 'r')
        zip_ref.extractall(self.tmp_dir)
        zip_ref.close()

        filezilla = lief.parse(sample)

        builder = lief.PE.Builder(filezilla)
        builder.build_resources(True)
        builder.build()
        builder.write(output)

        st = os.stat(output)
        os.chmod(output, st.st_mode | stat.S_IEXEC)

        if sys.platform.startswith("win"):
            subprocess_flags = 0x8000000 # win32con.CREATE_NO_WINDOW?
            p = Popen(["START", output], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess_flags)
            time.sleep(3)
            q = Popen(["taskkill", "/im", "filezilla_rsrc.exe"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            stdout, _ = p.communicate()
            self.logger.debug(stdout.decode("utf8"))

            stdout, _ = q.communicate()
            self.logger.debug(stdout.decode("utf8"))

            self.assertEqual(q.returncode, 0)






    def tearDown(self):
        # Delete it
        try:
            if os.path.isdir(self.tmp_dir):
                shutil.rmtree(self.tmp_dir)
        except Exception as e:
            self.logger.error(e)



if __name__ == '__main__':

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    root_logger.addHandler(ch)

    unittest.main(verbosity=2)

