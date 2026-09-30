// Software releases shown on the page: download buttons, version labels and
// the "What's new" panel all read from here.
//
// Normally this file is updated with tools/release_notes.py, which reads
// the git history of each program and turns the commits into readable notes
// (see README.md). It can also be edited by hand: the part after
// "window.SOFTWARE =" must stay valid JSON (double quotes, no trailing commas).
//
// Note types: "new", "improved", "fixed".
// "commit" is the commit each zip was built from: the notes of a release
// describe exactly what is inside its zip.

window.SOFTWARE = {
  "panda": {
    "name": "PANDA",
    "repo": "../Panda",
    "version_file": "src/app/metadata.py",
    "latest": {
      "version": "1.0.65",
      "date": "2026-09-29",
      "file": "downloads/PANDA_v1.0.65_Windows_x64.zip",
      "size": "177 MB",
      "manual": "downloads/PANDA_User_Manual_v1.0.65.pdf"
    },
    "releases": [
      {
        "version": "1.0.65",
        "date": "2026-09-29",
        "commit": "9c5e144",
        "notes": [
          {"type": "improved", "text": "Maintenance release."}
        ]
      },
      {
        "version": "1.0.64",
        "date": "2026-09-28",
        "commit": "1838ca2",
        "notes": [
          {"type": "new", "text": "Pretreated 1D data in <code>.xy</code> files (2θ and intensity only) can be loaded; uncertainties are estimated as √I, with a minimum of 1 count."},
          {"type": "new", "text": "D2B virtual detector: the save dialog can export the image as XYZS or Origin ASCII (γ, vertical pixel, counts), as the heatmap already could."},
          {"type": "improved", "text": "<code>.xys</code>, <code>.dat</code> and <code>.xy</code> files: a <code>Wavelength = value</code> header line is read as the wavelength and shown in the Wavelength (Å) column."},
          {"type": "improved", "text": "D16 and XtremeD: the uncertainty of each 2θ channel is now the purely statistical (Poisson) error propagated from the detector pixels. Refinements of these data give honest χ² values that reflect how well the model fits. D2B is unchanged."},
          {"type": "new", "text": "The user manual explains how the 2D-detector uncertainties are computed."}
        ]
      },
      {
        "version": "1.0.63",
        "date": "2026-08-02",
        "notes": [
          {"type": "new", "text": "pyPRF: a Q button switches the Rietveld plot between the native axis and Q (Å⁻¹), for both constant-wavelength and time-of-flight data. Bragg ticks, excluded regions and hover values follow."},
          {"type": "new", "text": "The About dialog and the user manual can be opened from the start-up window, before loading any data."},
          {"type": "new", "text": "Background subtraction: a “None” option that only crops the excluded ranges, and an option to remove excluded ranges from the output."},
          {"type": "improved", "text": "D16 and XtremeD uncertainties use the error of the mean over the pixels of each 2θ channel instead of their spread, which overestimated them."}
        ]
      },
      {
        "version": "1.0.62",
        "date": "2026-08-01",
        "notes": [
          {"type": "new", "text": "Automatic background subtraction for all selected runs, with seven estimators (Chebyshev — the default —, arPLS, AsLS, SNIP, rolling ball, Bruckner and spline), a live preview and hand-editable anchor points. The corrected patterns are collected in a new workspace."},
          {"type": "fixed", "text": "Font size of the data trees on high-resolution screens."}
        ]
      },
      {
        "version": "1.0.61",
        "date": "2026-07-22",
        "notes": [
          {"type": "new", "text": "Workspace tabs can be renamed (double-click or right-click)."},
          {"type": "new", "text": "PANDA can be opened from inside the FullProf Toolbar."},
          {"type": "improved", "text": "Detector calibration files are shipped with the program."}
        ]
      },
      {
        "version": "1.0.58",
        "date": "2026-07-19",
        "notes": [
          {"type": "new", "text": "Motor and sample-environment values recorded in the NeXus files are read and shown in tables, to pick and compare runs."},
          {"type": "improved", "text": "Differences between runs and normalisation to monitor are more robust."},
          {"type": "improved", "text": "Several small improvements in the pyPRF viewer."}
        ]
      },
      {
        "version": "1.0.22",
        "date": "2026-07-07",
        "notes": [
          {"type": "new", "text": "Files load in the background: the window opens immediately, the status bar shows progress and loading can be cancelled."},
          {"type": "improved", "text": "Exported <code>.xys</code> files record the efficiency-calibration file used."},
          {"type": "improved", "text": "Problems with time normalisation are reported once, as a summary, instead of one dialog per run."}
        ]
      },
      {
        "version": "1.0.8",
        "date": "2026-06-27",
        "notes": [
          {"type": "new", "text": "Virtual detector: a slice panel shows the 1D profile, with an integration window of 1–128 rows drawn on the detector image."},
          {"type": "improved", "text": "Right-click undoes the last zoom in results and 2D views as well."}
        ]
      },
      {
        "version": "1.0.7",
        "date": "2026-06-26",
        "notes": [
          {"type": "new", "text": "Time-of-flight data get their own tab; the Q-space conversion adapts to constant-wavelength or TOF data."},
          {"type": "new", "text": "Sequential fitting and analysis of D1B data."},
          {"type": "improved", "text": "At start-up PANDA checks the installed library versions and warns about known incompatible ones."}
        ]
      },
      {
        "version": "1.0.0",
        "date": "2026-06-17",
        "notes": [
          {"type": "improved", "text": "PANDA 1.0: the code has been reorganised as a tested package with the same scientific behaviour as classic PANDA, making it easier to maintain and to build for Windows and Linux."}
        ]
      },
      {
        "version": "0.9.109",
        "date": "2026-05-30",
        "notes": [
          {"type": "new", "text": "Time-of-flight powder data in GSAS / ISIS format."},
          {"type": "improved", "text": "Axis labels of the 1D, 2D and 3D views follow the kind of data shown."},
          {"type": "improved", "text": "Data files are recognised with or without an extension."},
          {"type": "improved", "text": "pyPRF: more robust handling of excluded regions, and a fix for the hover information."},
          {"type": "improved", "text": "Faster start-up; PANDA can run as a stand-alone program."}
        ]
      },
      {
        "version": "0.9.60",
        "date": "2026-05-27",
        "notes": [
          {"type": "new", "text": "Advanced settings dialog to adjust the visualisation."},
          {"type": "improved", "text": "The 3D views were rebuilt with VisPy (OpenGL): much smoother with large data sets."}
        ]
      },
      {
        "version": "0.9.2",
        "date": "2026-05-25",
        "notes": [
          {"type": "new", "text": "Reads XYS / DAT files (2θ, intensity, error and header metadata) and PANalytical XRDML files."},
          {"type": "new", "text": "D16 support (fixed scans)."},
          {"type": "new", "text": "PANDA opens even when the working folder has no NeXus files."},
          {"type": "new", "text": "Dark mode, also in pyPRF."},
          {"type": "new", "text": "pyPRF, the viewer for FullProf Rietveld results, is included."}
        ]
      },
      {
        "version": "0.9",
        "date": "2026-04",
        "notes": [
          {"type": "new", "text": "Support for instruments with 2D detectors (D2B, XtremeD), including scans that are still running."},
          {"type": "improved", "text": "Parallel reading of data over the network."},
          {"type": "improved", "text": "New Qt 6 (PySide6) interface with light and dark themes; runs on Windows, Linux and macOS."}
        ]
      }
    ]
  },
  "editpycr": {
    "name": "Edit_PyCR",
    "repo": "../Edit_PyCR",
    "version_file": "src/edit_pycr/core/app_version.py",
    "latest": {
      "version": "0.4.0",
      "date": "2026-09-29",
      "file": "downloads/Edit_PyCR_v0.4.0_Windows_x64.zip",
      "size": "76 MB",
      "manual": "downloads/Edit_PyCR_User_Manual_v0.4.0.pdf"
    },
    "releases": [
      {
        "version": "0.4.0",
        "date": "2026-09-29",
        "commit": "3064070",
        "notes": [
          {"type": "fixed", "text": "The mCIF to PCR conversion (Create > From mCIF) no longer crashes on many mCIF files, including FullProf's own <code>dy2.mcif</code>."},
          {"type": "new", "text": "“Edit instrument parameters...” now has a “Refine” checkbox next to every refinable field, such as Zero, SyCos, SySin, Lambda, their TOF equivalents and the Thermal/epithermal cross-over group. The dialog is now laid out in two columns."},
          {"type": "new", "text": "When FullProf stops on a singular matrix, the refining window now says so. It names the parameter and its refinement code and lists the <code>.pcr</code> lines that use that code."},
          {"type": "new", "text": "New “Edit Results” menu, as in the FullProf Toolbar, which opens in editor tabs any file named after the current job, such as <code>.out</code>, <code>.sum</code> or <code>.prf</code>."},
          {"type": "improved", "text": "Switching between light and dark theme in View > Theme now takes effect immediately, without a restart, and “Match the system” follows the desktop when it changes."},
          {"type": "improved", "text": "The refinement history's “Chi2 (per phase)” tab is now “Chi2 (per pattern)” and shows each pattern's Chi2, read from the run's <code>.sum</code> file."},
          {"type": "fixed", "text": "Simulated Annealing searches whose cost is not Chi-square, such as single-crystal <R-factor(F2)> searches, now show progress and a best configuration."},
          {"type": "new", "text": "Floating panels have a maximize/restore button that fills the screen they are on, and a thin border. A panel is now undocked or docked again by double-clicking its title bar."},
          {"type": "improved", "text": "During long Simulated Annealing searches, the refining window's equalizer keeps fixed-size cells and scrolls them all with one shared scrollbar. It follows the latest step unless you scroll back."},
          {"type": "fixed", "text": "The refining window's Text output now stays where you scrolled instead of jumping to the bottom with every new line."},
          {"type": "fixed", "text": "Best Configuration card: the scrollbar no longer covers the refined values, the header no longer wraps onto two lines, and rows line up with long parameter lists. The statistics card is no longer cut short at the end of a run."},
          {"type": "fixed", "text": "Hover definitions now work for keywords that contain punctuation, such as Strain-Model, Sig-2 or Tolerance(%)."},
          {"type": "fixed", "text": "Floating panels keep the theme colours on their title bar and frame instead of showing Qt's default grey."},
          {"type": "fixed", "text": "The tables in the Excluded regions and Background dialogs are no longer white in dark mode."}
        ]
      },
      {
        "version": "0.3.0",
        "date": "2026-09-23",
        "commit": "a266a4e",
        "notes": [
          {"type": "new", "text": "Simulated-annealing searches (Cry=3) are shown as such, with a table of the best configuration found, instead of looking like a failed refinement."},
          {"type": "improved", "text": "Live pattern during a refinement: excluded points are detected directly, half-written snapshots are skipped, and Bragg-tick colours are right for superspace files."},
          {"type": "improved", "text": "Inactive documents collapse automatically in the structure tree, and the tree scrolls while a phase is dragged."},
          {"type": "fixed", "text": "A run ending with “=> END Date” is recognised as finished normally."},
          {"type": "fixed", "text": "Spin-box arrows no longer overlap their number on some screens."}
        ]
      },
      {
        "version": "0.2.1",
        "date": "2026-09-21",
        "notes": [
          {"type": "new", "text": "Refinement summary and “Check this file” tools, and an action to stop a running FullProf."},
          {"type": "improved", "text": "Dock panels can be grouped as tabs."},
          {"type": "fixed", "text": "Newly enabled global VARY / FIX groups are merged into their existing line; the file watcher no longer hangs on non-PCR tabs."}
        ]
      },
      {
        "version": "0.2.0",
        "date": "2026-09-13",
        "notes": [
          {"type": "new", "text": "Now called Edit_PyCR, with a user manual."},
          {"type": "new", "text": "Sequential refinement over a numbered series of data files, and refinement strategies that release parameters in stages."},
          {"type": "new", "text": "Atoms editor and structure import from CIF; editors for profile shape, anisotropic strain (Laue-class models) and extinction."},
          {"type": "new", "text": "Conversion between Rietveld and profile matching; several phases and patterns can be combined into one file."},
          {"type": "new", "text": "Background refinement starting from selected points, with starting values for analytic backgrounds."},
          {"type": "new", "text": "Instrument-parameter dialog for constant-wavelength and TOF patterns; excluded-regions editor."},
          {"type": "new", "text": "CIF and mCIF → PCR conversion, including powder → single crystal and constant wavelength → TOF."},
          {"type": "new", "text": "Live pattern view during a refinement, and each history entry keeps its own <code>.prf</code>."},
          {"type": "improved", "text": "FullProf hints as tooltips, parameter renumbering and the cursor position shown on the pattern plot."}
        ]
      },
      {
        "version": "0.1.0",
        "date": "2026-08-30",
        "notes": [
          {"type": "new", "text": "First version: a FullProf <code>.pcr</code> editor with syntax highlighting, folding, keyword tooltips, autocompletion in Commands blocks and column (block) selection."},
          {"type": "new", "text": "Structure tree of experiments, phases and links: duplicate, delete or drag phases, edit cell parameters and refinement commands, fix all codes."},
          {"type": "new", "text": "Background editing from the tree: read or import points, change the background type, refine only the codes that need it."},
          {"type": "new", "text": "Run FullProf from the editor, with a refining window that follows the run; import or generate <code>.irf</code> files."},
          {"type": "new", "text": "Old single-pattern files can be converted to the multi-pattern layout; single-crystal blocks are supported."},
          {"type": "new", "text": "Light and dark themes that follow the desktop setting."}
        ]
      }
    ]
  }
};
