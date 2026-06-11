# JOBLOG Tracker UI Notes

## Recent cleanup

- Shared page chrome now lives in `ui_components.py`.
- Global colors, cards, session banner, buttons, form fields, and tables are styled in `styles.py`.
- `widgets/table_panel.py` precomputes transition/taper row colors when rows load instead of scanning the full model during every paint event.
- Table rows now hide vertical headers, avoid word wrapping, and use stable row heights for denser terminal views.

## Keep future pages consistent

- Use `action_button()` for primary page actions.
- Use `add_session_row()` at the top of signed-in pages.
- Use `add_header_row()` for page titles and right-aligned actions.
- Prefer table data preparation in `set_rows()` instead of delegates doing repeated work during paint.
