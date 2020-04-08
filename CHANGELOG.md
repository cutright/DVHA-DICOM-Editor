# Change log of DVHA DICOM Editor

v0.5 (TBD)
--------------------
 - Major rewrite for value enumeration to properly accommodate tags within a sequence
 - Fixed bug where a 2nd input-directory browse could cause crash
 - Ensure UIDs and random numbers generated in a session are unique from each other
 - Better minimum window size management
 - Optionally save edit history to csv file
 - Let user set "force" kwarg in pydicom.read_file()
 - Ignore files that are missing fhe following keyword properties:  
    'StudyDate', 'StudyTime', 'PatientID', 'StudyID', 'SeriesNumber'


v0.4 (2020.04.05)
--------------------
 - Random number generator functions: `vrand` and `frand`
 - Optionally set DICOM prefix and entropy source in "Advanced"
 - Keep cross-file UID connections by updating "Referenced" tags
 - Value functions no longer have an index parameter (parent DICOM elements don't have a value)

v0.3 (2020.03.31)
--------------------
 - Catch tag edit exceptions, display error log in window
 - Reorganized code so it is easier to follow, lots of comments added
 - Search for DICOM tags
 - Values can be dynamically defined based on file_path or current tag values
 - Thread file parsing with progress bar
 - Ability to search sub folders
 
 
v0.2 (2020.03.27)
--------------------
 - Allow user to select a file to pre-populate the value input
 - Update description key up for more intuitive update
 - Save and load templates
 - Custom prepend string for file names

v0.1 (2020.03.25)
--------------------
 - Initial commit