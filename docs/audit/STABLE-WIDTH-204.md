# Stable editor width — 2.0.4

The code editor and input/output columns occupy 100% of their parent throughout execution. Variables, traces and errors render below the editor. Removed the JavaScript Bootstrap width switching (100% → 75%) and the trace CSS override (50%). Model settings use full-width labels/selects and stable scrollbar gutters.

Browser check on the generated site: editor column 960 px / parent row 960 px before execution, at step 1/54, after advancing, after completion and after selecting the factorial example. Inner code area remained 930 px (normal column padding). Execution completed and variables rendered.

JavaScript suite: 22 passed. macOS 2.0.4 app and DMG built successfully; hdiutil verification passed.
