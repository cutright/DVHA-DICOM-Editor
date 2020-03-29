<img src='https://user-images.githubusercontent.com/4778878/77683755-e0f94000-6f66-11ea-958c-a94c5c895266.png' align='right' width='400' alt="DVH Analytics screenshot">  

# DVHA DICOM Editor
Simple DICOM tag editor built with [wxPython](https://github.com/wxWidgets/Phoenix) and [pydicom](https://github.com/pydicom/pydicom)  
* No admin rights needed
* Executables provided, which require no installation  
* Create templates for routine tag editing
* Search for DICOM tags by keyword
* Dynamically define new DICOM tag values

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
Users can dynamically define DICOM tag values with one of the functions below, which are denoted by asterisk-pairs.

Available functions:
* `dir[n]`: insert the n<sup>th</sup> component of the file path
* `fenum[n]`: insert an iterator based on the  n<sup>th</sup> component of the file path
* `venum[n]`: insert an iterator based on the tag value, n=-1 being tag value, n=-2 the parent value, etc. 
(NOTE: only n=-1 is currently supported)

### Examples
For a directory `/some/file/path/ANON0001/` containing files `file_1.dcm`, `file_2.dcm`:
* *Directory*:
    * NOTE: file extensions are removed
    * `some_string_*dir[-1]*`
        * some_string_file_1
        * some_string_file_2
    * `*dir[-2]*_AnotherString`
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
    * `*dir[-2]*_*venum[-1]*` used with SOPInstanceUID tag
        * ANON0001_1
        * ANON0001_2
    * `*dir[-2]*_*venum[-1]*` used with StudyInstanceUID tag
        * ANON0001_1
        * ANON0001_1


This feature is still in development. Check back soon for more features.
