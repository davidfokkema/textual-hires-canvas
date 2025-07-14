# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.10.0] - 2025-07-14

### Changed

- Removed scale_rectangle attribute since that belongs in textual_plot.PlotWidget.

### Fixed

- Lots and lots of type hints.

## [0.9.0] - 2025-07-11

### Added

- Example to show off the improved rectangle algorithm [@edward-jazzhands]

### Fixed

- Fixed rendering of tiny rectangles with width or height of 2 or lower [@edward-jazzhands]

## [0.8.0] - 2025-05-24

### Changed

- Create the Canvas with a default size of 40x20 pixels.

## [0.7.0] - 2025-04-25

### Changed

- Lower Python version requirements back to 3.10.

## [0.6.0] - 2025-04-25

### Changed

- Massive performance overhaul, by @paulrobello (thanks!).

## [0.5.0] - 2025-03-11

### Added

- Analog clock example, by @ddkasa (thanks!).

### Changed

- Default HiResMode is now a public attribute.

## [0.4.0] - 2025-03-05

### Added

- Default HiResMode can now be specified when creating a Canvas object.
- Added rotating cube and torus example.

### Changed

- More consistent method naming

## [0.3.0] - 2025-02-21

### Added

- Added circle and filled circle normal / high-res drawing. [@paulrobello]
- Added FPS calculations and FPS graph to display. [@paulrobello]
- Added docstrings. [@paulrobello]

### Changed

- Improved performance a bit by simplifying strips.

## [0.2.0] - 2025-02-09

### Added

- Some basic usage examples in docs/examples.

### Changed

- `Canvas`, `HiResMode` and `TextAlign` can now be directly imported from `textual_hires_canvas`.
- No longer require Python 3.11 because 3.10 is good enough.

### Fixed

- Fixed type hints.

## [0.1.0] - 2025-02-09

Initial release.
