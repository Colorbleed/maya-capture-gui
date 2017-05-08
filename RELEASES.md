# Maya Capture GUI RELEASES

## 04 / 05 / 2017 - v1.3.2
- Solved issue #0030
  + Retrieved file path from "Browse" doesn't split unnecessary

## 04 / 05 / 2017 - v1.3.1
- Added token support for filename, example:  <Scene>_<Camera>_<RenderLayer>
- Solved issue #0026
  + Added "Raw frame number" checkbox, when using custom frames the user can enable to use the actual frame numbers in the file name. Example: playblast.0012.png

## 03 / 05 / 2017 - v1.3.0
- Changed mode name in Time Plugin, old presets incompatible with current version
- Removed unused keyword argument

## 03 / 05 / 2017 - v1.2.0
- Extended README with example of adding presets before launching the
tool
- Solved issue 0008
  + Playback of images, frame padding ( #### ) solved
  + View when finished works regardless of Save being checked
- Solved issue 0019
  + Non-chronological time range is not possible anymore
- Solved issue 0020
  + Added custom frame range, similar to print pages in Word

## 02 / 05 / 2017 - v1.1.0
- Solved issue 0014
- Added plugin validation function
- Added app validation function to validate listed plugins

## 24 / 04 / 2017 - v1.0.2
Fixed issue with storing presets and recent playblasts
Fixed issue with changing presets in selection box

## 24 / 04 / 2017 - v1.0.1

Resolved issue #11
Resolved issue #09

- Update Save options:
  + Choose to save to a location or keep it in the temp folder
  + Use default path : workspace/images
  + Use custom path: directory / file name

- Added menu for previous playblasts
- Added checkbox to control whether to open the playblast after capture

## 21 / 04 / 2017 - v1.0.0

- Time plugin updated when start and end frame are changed in widget
- Added "Save to default location" option