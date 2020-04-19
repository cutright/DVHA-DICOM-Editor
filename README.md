<img src='https://user-images.githubusercontent.com/4778878/78911640-2e3bde00-7a4c-11ea-900f-46119ee0044a.png' align='right' width='350' alt="DVH Analytics screenshot">  

# DVHA DICOM Editor
Simple DICOM tag editor built with [wxPython](https://github.com/wxWidgets/Phoenix) and [pydicom](https://github.com/pydicom/pydicom)  
* [Executables](https://github.com/cutright/DVHA-DICOM-Editor/releases) provided, which require no installation  
* Create templates for routine tag editing
* Search for DICOM tags by keyword
* Dynamically define new DICOM tag values based on:
    * File paths
    * Initial DICOM tag values
    * DICOM compliant UIDs
        * Lookup DICOM prefixes
        * Set entropy source for UID generation
        * Maintain cross-file UID links
    * Randomly generated numbers

<a href="https://pypi.org/project/dvha-edit/">
        <img src="https://img.shields.io/pypi/v/dvha-edit.svg"
             alt="PyPi Version" /></a>
<a href="https://lgtm.com/projects/g/cutright/DVHA-DICOM-Editor/context:python">
        <img src="https://img.shields.io/lgtm/grade/python/g/cutright/DVHA-DICOM-Editor.svg?logo=lgtm&label=code%20quality"
             alt="LGTM Python Code Quality" /></a>

Source-Code Installation
---------
To install via pip:
```
pip install dvha-edit
```
If you've installed via pip or setup.py, launch from your terminal with:
```
dvhaedit
```
If you've cloned the project, but did not run the setup.py installer, launch DVHA DICOM Editor with:
```
python dvhaedit_app.py
```

Dynamic Value Setting
------------------------------------------------------------------------------
Users can dynamically define new DICOM tag values based on file path or initial DICOM tag values.

### Available Functions
* File path / Tag Value:
    * `file[n]`: the n<sup>th</sup> component of the file path
    * `val`: DICOM tag value
* Enumeration:
    * `fenum[n]`: an iterator based on `file[n]`
    * `venum`: an iterator based on `val` 
* DICOM UID
    * `fuid[n]` and `vuid`: same as `fenum`/`venum`, except the enumeration value is replaced with a 
    DICOM compliant UID
* Random Number
    * `frand[n]` and `vrand`: same as DICOM UID functions except the value is a random integer

### Examples
For a directory `/some/file/path/ANON0001/` containing files `file_1.dcm`, `file_2.dcm`:
* *Directory*:
    * NOTE: file extensions are removed
    * `some_string_*file[-1]*`
        * some_string_file_1
        * some_string_file_2
    * `*file[-2]*_AnotherString`
        * ANON0001_AnotherString
        * ANON0001_AnotherString
* *File Enumeration*:
    * `some_string_*fenum[-1]*`
        * some_string_1
        * some_string_2
    * `*fenum[-2]*_AnotherString`
        * 1_AnotherString
        * 1_AnotherString
* *Value Enumeration*:
    * NOTE: Assume these two files have the same StudyInstanceUID but different SOPInstanceUIDs
    * `*file[-2]*_*venum*` used with SOPInstanceUID tag
        * ANON0001_1
        * ANON0001_2
    * `*file[-2]*_*venum*` used with StudyInstanceUID tag
        * ANON0001_1
        * ANON0001_1

MultiValue Tags
------------------------------------------------------------------------------
Some DICOM tags point to multiple values (i.e., MultiValue pydicom class). As of 
DVHA DICOM Editor v0.6, a new DICOM tag value can be interpreted as a list if it begins 
with `[`, ends with `]`, and uses `, ` (comma-space) as a separator (this is the same 
format as python's `str` representation of a list). Do not add quotes to make an item a string. 
All value typing is handled by pydicom.

### Example
The DICOM tag `ImageOrientationPatient` (0020, 0037) is a list of 6 integers. If you want 
this orientation to be head first-supine (HFS), it's value should be set to `[1, 0, 0, 0, 1, 0]`. 