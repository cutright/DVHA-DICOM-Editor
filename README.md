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
Dynamic values are denoted by encapsulating asterisks.

Available functions:
* `dir[n]`: insert the n<sup>th</sup> component of the file path
* `enum[n]`: insert an iterator based on the  n<sup>th</sup> component of the file path

Examples, for a dir `/home/any_dir_name/` containing files `file_1.dcm`, `file_2.dcm`:
* Directory:
    * `some_string_*dir[-1]*`
        * some_string_file_1.dcm
        * some_string_file_2.dcm
    * `*dir[-2]*_AnotherString`
        * any_dir_name_AnotherString
        * any_dir_name_AnotherString
* Enumeration:
    * `some_string_*enum[-1]*`
        * some_string_1
        * some_string_2
    * `*enum[-2]*_AnotherString`
        * 1_AnotherString
        * 1_AnotherString


This feature is still in development. Check back soon for more features.
