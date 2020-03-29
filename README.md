<img src='https://user-images.githubusercontent.com/4778878/77683755-e0f94000-6f66-11ea-958c-a94c5c895266.png' align='right' width='350' alt="DVHA DICOM Editor screenshot">
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

Currently, the only function available is `dir`. If `*dir[n]*` is in your value, it will be 
replaced with the n<sup>th</sup> component of the file path for the file being edited.

For example, for a file `/some/file/path/your_file.dcm`:
* `some_string_*dir[-1]*` -->  `some_string_your_file`
* `*dir[-2]*_AnotherString` --> `path_AnotherString`


This feature is still in development. Check back soon for more features.
