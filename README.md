<img src='https://user-images.githubusercontent.com/4778878/77955388-b7595500-7295-11ea-9977-31c01a44e1a2.png' align='right' width='400' alt="DVH Analytics screenshot">  

# DVHA DICOM Editor
Simple DICOM tag editor built with [wxPython](https://github.com/wxWidgets/Phoenix) and [pydicom](https://github.com/pydicom/pydicom)  
* No admin rights needed
* Executables provided, which require no installation  
* Create templates for routine tag editing
* Search for DICOM tags by keyword
* Dynamically define new DICOM tag values based on:
    * File paths
    * Initial DICOM tag values
    * DICOM compliant UIDs

<a href="https://pypi.org/project/dvha-edit/">
        <img src="https://img.shields.io/pypi/v/dvha-edit.svg" /></a>
<a href="https://lgtm.com/projects/g/cutright/DVHA-DICOM-Editor/context:python">
        <img src="https://img.shields.io/lgtm/grade/python/g/cutright/DVHA-DICOM-Editor.svg?logo=lgtm&label=code%20quality" /></a>


Installation
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
Or check out the [Releases](https://github.com/cutright/DVHA-DICOM-Editor/releases) page for an executable.

Dynamic Value Setting
---------
Users can dynamically define new DICOM tag values based on file path or initial DICOM tag values.

### Available Functions
* File path / Tag Value:
    * `file[n]`: the n<sup>th</sup> component of the file path
    * `val[n]`: DICOM tag value, n=-1 being tag value, n=-2 the parent value, etc.
* Enumeration:
    * `fenum[n]`: an iterator based on `file[n]`
    * `venum[n]`: an iterator based on `val[n]` 
* DICOM UID
    * `fuid[n]` and `vuid[n]`: same as `fenum`/`venum`, except the enumeration value is replaced with a DICOM compliant UID

**NOTE**: DICOM tags that are within sequences are not yet enabled, so `val`, `venum`, and `vuid` functions 
currently ignore `n`, although n must still be an integer.

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
    * NOTE: Assume each file has the same StudyInstanceUID but different SOPInstanceUIDs
    * `*file[-2]*_*venum[-1]*` used with SOPInstanceUID tag
        * ANON0001_1
        * ANON0001_2
    * `*file[-2]*_*venum[-1]*` used with StudyInstanceUID tag
        * ANON0001_1
        * ANON0001_1
