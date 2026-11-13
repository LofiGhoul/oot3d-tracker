#!/usr/bin/env python3
"""Ocarina of Time 3D 100% Tracker — GTK4 / libadwaita front end."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import oot3d_save as mm  # noqa: E402

APP_ID = "io.github.oot3d_tracker"
STATE_FILE = Path(GLib.get_user_config_dir()) / "oot3d-tracker" / "state.json"
HEARTS = "hearts"

CSS = """
.hero-count { font-size: 42px; font-weight: 800; font-feature-settings: "tnum"; }
.hero-total { font-size: 20px; font-weight: 600; opacity: .55; }
.piece-icon { border-radius: 999px; min-width: 30px; min-height: 30px; }
.piece-icon.got { background: alpha(@success_color, .18); color: @success_color; }
.piece-icon.maybe { background: alpha(@warning_color, .18); color: @warning_color; }
.piece-icon.missing { background: alpha(@window_fg_color, .07); color: alpha(@window_fg_color, .35); }
.cat-icon { border-radius: 10px; min-width: 36px; min-height: 36px;
            background: alpha(@accent_bg_color, .18); color: @accent_color; }
.cat-icon.done { background: alpha(@success_color, .18); color: @success_color; }
row.got-row .title { opacity: .6; }
image.not-owned { opacity: .25; filter: grayscale(1); }
.region-chip { border-radius: 999px; padding: 2px 10px; font-size: 12px; font-weight: 600;
               background: alpha(@window_fg_color, .07); }
.region-chip.done { background: alpha(@success_color, .18); color: @success_color; }
.step-num { border-radius: 999px; min-width: 22px; min-height: 22px; font-size: 12px;
            font-weight: 700; background: alpha(@accent_bg_color, .2); color: @accent_color; }
progressbar.thin trough, progressbar.thin progress { min-height: 6px; border-radius: 99px; }
progressbar.big trough, progressbar.big progress { min-height: 10px; border-radius: 99px; }
progressbar.done progress { background: @success_color; }
"""


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state))
    except OSError:
        pass


def heart_path(cr, x, y, s):
    cr.move_to(x + s / 2, y + s * 0.92)
    cr.curve_to(x - s * 0.05, y + s * 0.5, x + s * 0.02, y + s * 0.02, x + s * 0.27, y + s * 0.06)
    cr.curve_to(x + s * 0.4, y + s * 0.08, x + s * 0.48, y + s * 0.18, x + s / 2, y + s * 0.26)
    cr.curve_to(x + s * 0.52, y + s * 0.18, x + s * 0.6, y + s * 0.08, x + s * 0.73, y + s * 0.06)
    cr.curve_to(x + s * 0.98, y + s * 0.02, x + s * 1.05, y + s * 0.5, x + s / 2, y + s * 0.92)
    cr.close_path()


class HeartMeter(Gtk.DrawingArea):
    """In-game style heart row: full hearts plus a quarter-filled one in progress."""

    SIZE, GAP, PER_ROW = 22, 4, 10

    def __init__(self, full: int, quarters: int):
        super().__init__()
        self.full, self.quarters = full, quarters
        n = full + (1 if quarters else 0)
        self.set_content_width(min(max(n, 1), self.PER_ROW) * (self.SIZE + self.GAP))
        self.set_content_height(max(1, math.ceil(n / self.PER_ROW)) * (self.SIZE + self.GAP))
        self.set_draw_func(self._draw)

    def _draw(self, _area, cr, _w, _h):
        s, g = self.SIZE, self.GAP
        items = [1.0] * self.full + ([self.quarters / 4] if self.quarters else [])
        for i, fill in enumerate(items):
            x = (i % self.PER_ROW) * (s + g) + 1
            y = (i // self.PER_ROW) * (s + g) + 1
            heart_path(cr, x, y, s - 2)
            cr.set_source_rgba(0.9, 0.28, 0.3, 0.18)
            cr.fill()
            cr.save()
            heart_path(cr, x, y, s - 2)
            cr.clip()
            cr.move_to(x + s / 2, y + s / 2)
            cr.arc(x + s / 2 - 1, y + s / 2, s, -math.pi / 2, -math.pi / 2 + 2 * math.pi * fill)
            cr.close_path()
            cr.set_source_rgb(0.9, 0.28, 0.3)
            cr.fill()
            cr.restore()
            heart_path(cr, x, y, s - 2)
            cr.set_source_rgba(0.55, 0.1, 0.12, 0.9)
            cr.set_line_width(1.2)
            cr.stroke()


def heart_icon() -> Gtk.Widget:
    area = Gtk.DrawingArea(content_width=20, content_height=20, margin_start=8, margin_end=8,
                           valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)

    def draw(_a, cr, _w, _h):
        heart_path(cr, 1, 1, 18)
        cr.set_source_rgb(0.9, 0.28, 0.3)
        cr.fill()
    area.set_draw_func(draw)
    box = Gtk.Box(valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER, hexpand=False)
    box.add_css_class("cat-icon")
    box.append(area)
    return box


def status_icon(status: str | None, tip_inferred: str = "") -> Gtk.Widget:
    icon_name, cls, tip = {
        "yes": ("object-select-symbolic", "got", "Done"),
        "inferred": ("dialog-question-symbolic", "maybe", tip_inferred),
        None: ("radio-symbolic", "missing", "Not done yet"),
    }[status]
    img = Gtk.Image(icon_name=icon_name, valign=Gtk.Align.CENTER, tooltip_text=tip)
    img.add_css_class("piece-icon")
    img.add_css_class(cls)
    return img


def progress_bar(done: int, total: int, css: str) -> Gtk.ProgressBar:
    bar = Gtk.ProgressBar(fraction=done / total if total else 0, valign=Gtk.Align.CENTER)
    bar.add_css_class(css)
    if total and done == total:
        bar.add_css_class("done")
    return bar


def chip(text: str, done: bool) -> Gtk.Label:
    lbl = Gtk.Label(label=text, valign=Gtk.Align.CENTER)
    lbl.add_css_class("region-chip")
    if done:
        lbl.add_css_class("done")
    return lbl


# Optional icons you supply yourself (none ship with the app). A file named after the
# check id without its prefix, e.g. "hookshot.png" for i_hookshot, "lullaby.png" for s_lullaby.
ICON_DIRS = (
    Path(__file__).resolve().parent / "icons",
    Path(GLib.get_user_data_dir()) / "oot3d-tracker" / "icons",
)
ICON_EXTS = (".png", ".svg", ".webp", ".jpg", ".jpeg")
_icon_cache: dict[str, Path | None] = {}


def find_icon(check_id: str) -> Path | None:
    if check_id not in _icon_cache:
        stem = check_id.split("_", 1)[-1]
        _icon_cache[check_id] = next(
            (d / f"{stem}{ext}" for d in ICON_DIRS for ext in ICON_EXTS if (d / f"{stem}{ext}").is_file()),
            None)
    return _icon_cache[check_id]


def item_picture(path: Path, owned: bool, size: int) -> Gtk.Widget:
    pic = Gtk.Image.new_from_file(str(path))
    pic.set_pixel_size(size)
    pic.set_valign(Gtk.Align.CENTER)
    if not owned:
        pic.add_css_class("not-owned")
    return pic


class TrackerWindow(Adw.ApplicationWindow):
    def __init__(self, app, initial: Path | None):
        super().__init__(application=app, title="OoT3D 100% Tracker")
        self.set_default_size(560, 860)
        self.state = load_state()
        self.slots: list[Path] = []
        self.current: Path | None = None
        self.result: mm.SlotResult | None = None
        self.monitor: Gio.FileMonitor | None = None
        self._reload_id = 0
        self.filter_mode = self.state.get("filter", "all")
        self.detail_page: Adw.NavigationPage | None = None
        self.detail_cat: str | None = None
        self.detail_scroller: Gtk.ScrolledWindow | None = None

        self.toasts = Adw.ToastOverlay()
        self.nav = Adw.NavigationView()
        self.nav.connect("popped", self._on_popped)
        self.toasts.set_child(self.nav)
        self.set_content(self.toasts)

        # ---- overview page ----
        view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        open_btn = Gtk.Button(icon_name="document-open-symbolic", tooltip_text="Open save file (Ctrl+O)")
        open_btn.connect("clicked", lambda *_: self.choose_file())
        header.pack_start(open_btn)
        self.reload_btn = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Reload (Ctrl+R)",
                                     sensitive=False)
        self.reload_btn.connect("clicked", lambda *_: self.reload())
        header.pack_start(self.reload_btn)
        self.title = Adw.WindowTitle(title="100% Tracker", subtitle="Ocarina of Time 3D")
        header.set_title_widget(self.title)
        view.add_top_bar(header)

        self.slot_bar = Gtk.Box(margin_start=12, margin_end=12, margin_top=6, margin_bottom=6, visible=False)
        self.slot_group = Adw.ToggleGroup(hexpand=True)
        self.slot_group.add_css_class("round")
        self.slot_group.connect("notify::active-name", self._on_slot_toggled)
        self.slot_bar.append(self.slot_group)
        view.add_top_bar(self.slot_bar)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        empty = Adw.StatusPage(
            icon_name="document-open-symbolic",
            title="Open your save",
            description="Pick an Ocarina of Time 3D save slot file\n"
                        "from Checkpoint/JKSM or a 3DS emulator, or drop it on this window.",
        )
        btn = Gtk.Button(label="Open Save File…", halign=Gtk.Align.CENTER)
        btn.add_css_class("pill")
        btn.add_css_class("suggested-action")
        btn.connect("clicked", lambda *_: self.choose_file())
        empty.set_child(btn)
        self.stack.add_named(empty, "empty")
        self.overview_scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.stack.add_named(self.overview_scroller, "overview")
        view.set_content(self.stack)
        self.nav.add(Adw.NavigationPage(child=view, title="Overview", tag="overview"))

        drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop.connect("drop", self._on_drop)
        self.add_controller(drop)
        ctl = Gtk.ShortcutController()
        for accel, cb in (("<Control>o", self.choose_file), ("<Control>r", self.reload)):
            ctl.add_shortcut(Gtk.Shortcut(trigger=Gtk.ShortcutTrigger.parse_string(accel),
                                          action=Gtk.CallbackAction.new(lambda *_a, f=cb: (f(), True)[1])))
        self.add_controller(ctl)

        start = initial
        if start is None and self.state.get("last") and Path(self.state["last"]).is_file():
            start = Path(self.state["last"])
        if start is None:
            found = mm.discover_saves()
            start = found[0] if found else None
        if start:
            self.open_path(start)

    # ---- file handling ------------------------------------------------------
    def choose_file(self):
        dlg = Gtk.FileDialog(title="Open Ocarina of Time 3D save")
        f = Gtk.FileFilter(name="OoT3D save slots")
        f.add_pattern("*.bin")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dlg.set_filters(filters)
        if self.current:
            dlg.set_initial_folder(Gio.File.new_for_path(str(self.current.parent)))
        dlg.open(self, None, self._on_file_chosen)

    def _on_file_chosen(self, dlg, res):
        try:
            gfile = dlg.open_finish(res)
        except GLib.Error:
            return
        if gfile and gfile.get_path():
            self.open_path(Path(gfile.get_path()))

    def _on_drop(self, _target, value, _x, _y):
        files = value.get_files()
        if files and files[0].get_path():
            self.open_path(Path(files[0].get_path()))
            return True
        return False

    def open_path(self, path: Path):
        try:
            mm.read_slot(path)
        except (OSError, mm.SaveError) as e:
            self.toasts.add_toast(Adw.Toast(title=str(e), timeout=6))
            return
        self.slots = mm.find_slot_siblings(path)
        if path not in self.slots:
            self.slots = [path]
        self.slot_group.remove_all()
        for i, p in enumerate(self.slots):
            try:
                label = mm.read_slot(p).player_name
            except (OSError, mm.SaveError):
                label = p.stem
            num = i + 1
            self.slot_group.add(Adw.Toggle(name=str(p), label=f"{num} · {label}", tooltip=str(p)))
        self.slot_bar.set_visible(len(self.slots) > 1)
        self.current = path  # so the toggle handler below doesn't load it a second time
        self.slot_group.set_active_name(str(path))
        self.show_slot(path)

    def _on_slot_toggled(self, group, _pspec):
        name = group.get_active_name()
        if name and (self.current is None or name != str(self.current)):
            self.show_slot(Path(name))

    def show_slot(self, path: Path):
        self.current = path
        self.state["last"] = str(path)
        save_state(self.state)
        if self.monitor:
            self.monitor.cancel()
        self.monitor = Gio.File.new_for_path(str(path)).monitor_file(Gio.FileMonitorFlags.NONE, None)
        self.monitor.connect("changed", self._on_file_changed)
        self.reload(quiet=True)

    def _on_file_changed(self, *_):
        if self._reload_id:
            GLib.source_remove(self._reload_id)
        self._reload_id = GLib.timeout_add(400, self._delayed_reload)

    def _delayed_reload(self):
        self._reload_id = 0
        self.reload(auto=True)
        return GLib.SOURCE_REMOVE

    def reload(self, quiet: bool = False, auto: bool = False):
        if not self.current:
            return
        try:
            self.result = mm.read_slot(self.current)
        except (OSError, mm.SaveError) as e:
            self.toasts.add_toast(Adw.Toast(title=f"Couldn't read save: {e}", timeout=6))
            return
        self._set_scrolled(self.overview_scroller, self._build_overview(self.result), keep=auto)
        if self.detail_cat and self.detail_scroller:
            self._set_scrolled(self.detail_scroller, self._build_detail(self.detail_cat), keep=True)
        self.stack.set_visible_child_name("overview")
        self.reload_btn.set_sensitive(True)
        mq = " · Master Quest" if self.result.master_quest else ""
        self.title.set_subtitle(f"{self.result.player_name} — {self.current.name}{mq}")
        if not quiet:
            self.toasts.add_toast(Adw.Toast(title="Save changed — updated" if auto else "Reloaded", timeout=2))

    @staticmethod
    def _set_scrolled(scroller: Gtk.ScrolledWindow, child: Gtk.Widget, keep: bool):
        pos = scroller.get_vadjustment().get_value() if keep else 0.0
        scroller.set_child(Gtk.Viewport(scroll_to_focus=False, child=child))

        def restore():
            scroller.get_vadjustment().set_value(pos)
            return GLib.SOURCE_REMOVE
        GLib.idle_add(restore)

    # ---- overview -------------------------------------------------------------
    def _build_overview(self, r: mm.SlotResult) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                       margin_top=18, margin_bottom=30, margin_start=12, margin_end=12)
        page.append(self._summary_card(r))

        group = Adw.PreferencesGroup(title="Checklist")
        group.add(self._category_row(HEARTS, "Pieces of Heart", None, r.collected_count, mm.TOTAL_PIECES))
        for cat, rows in r.categories:
            done = sum(1 for _c, ok, _d in rows if ok)
            group.add(self._category_row(cat.id, cat.title, cat.icon, done, len(rows)))
        page.append(group)

        note = Gtk.Label(
            label="Not tracked: the trading sequences, masks, Big Poe captures, cows and "
                  "small keys. Their rewards that matter for 100% are covered above.",
            wrap=True, xalign=0)
        note.add_css_class("caption")
        note.add_css_class("dim-label")
        page.append(note)
        return Adw.Clamp(maximum_size=640, child=page)

    def _summary_card(self, r: mm.SlotResult) -> Gtk.Widget:
        done, total = r.overall
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        card.add_css_class("card")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                        margin_top=16, margin_bottom=16, margin_start=18, margin_end=18)
        card.append(inner)

        top = Gtk.Box(spacing=12)
        nums = Gtk.Box(spacing=2, valign=Gtk.Align.END)
        pct = Gtk.Label(label=f"{math.floor(100 * done / total)}")
        pct.add_css_class("hero-count")
        sign = Gtk.Label(label="%", valign=Gtk.Align.BASELINE)
        sign.add_css_class("hero-total")
        nums.append(pct)
        nums.append(sign)
        top.append(nums)
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, hexpand=True)
        t = Gtk.Label(label="Completion", xalign=0)
        t.add_css_class("heading")
        sub = Gtk.Label(label=f"{done} of {total} checks done", xalign=0)
        sub.add_css_class("dim-label")
        side.append(t)
        side.append(sub)
        top.append(side)
        inner.append(top)
        inner.append(progress_bar(done, total, "big"))
        inner.append(HeartMeter(r.heart_containers, r.pieces_in_progress))
        info = Gtk.Label(label=f"{r.heart_containers} hearts · {r.pieces_in_progress}/4 toward the next",
                         xalign=0)
        info.add_css_class("caption")
        info.add_css_class("dim-label")
        inner.append(info)
        return card

    def _category_row(self, cat_id, title, icon, done, total) -> Gtk.Widget:
        row = Adw.ActionRow(title=GLib.markup_escape_text(title), activatable=True,
                            subtitle=f"{done} / {total}" + ("  ·  complete" if done == total else ""))
        if icon:
            img = Gtk.Image(icon_name=icon, valign=Gtk.Align.CENTER)
            img.add_css_class("cat-icon")
            if done == total:
                img.add_css_class("done")
            row.add_prefix(img)
        else:
            row.add_prefix(heart_icon())
        bar = progress_bar(done, total, "thin")
        bar.set_size_request(90, -1)
        row.add_suffix(bar)
        row.add_suffix(Gtk.Image(icon_name="go-next-symbolic"))
        row.connect("activated", lambda *_: self.open_category(cat_id, title))
        return row

    # ---- category pages -------------------------------------------------------
    def open_category(self, cat_id: str, title: str):
        view = Adw.ToolbarView()
        header = Adw.HeaderBar()
        filt = Adw.ToggleGroup()
        filt.add(Adw.Toggle(name="all", label="All"))
        filt.add(Adw.Toggle(name="missing", label="Missing"))
        filt.set_active_name(self.filter_mode)
        filt.connect("notify::active-name", self._on_filter_toggled)
        header.pack_end(filt)
        view.add_top_bar(header)
        scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        view.set_content(scroller)
        page = Adw.NavigationPage(child=view, title=title)
        self.detail_page, self.detail_cat, self.detail_scroller = page, cat_id, scroller
        self._set_scrolled(scroller, self._build_detail(cat_id), keep=False)
        self.nav.push(page)

    def _on_popped(self, _nav, page):
        if page is self.detail_page:
            self.detail_page = self.detail_cat = self.detail_scroller = None

    def _on_filter_toggled(self, group, _pspec):
        self.filter_mode = group.get_active_name() or "all"
        self.state["filter"] = self.filter_mode
        save_state(self.state)
        if self.detail_cat and self.detail_scroller:
            self._set_scrolled(self.detail_scroller, self._build_detail(self.detail_cat), keep=False)

    def _build_detail(self, cat_id: str) -> Gtk.Widget:
        r = self.result
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                       margin_top=18, margin_bottom=30, margin_start=12, margin_end=12)
        clamp = Adw.Clamp(maximum_size=640, child=page)
        if r is None:
            return clamp
        if cat_id == HEARTS:
            shown = self._fill_hearts(page, r)
        else:
            cat, rows = next((c, rw) for c, rw in r.categories if c.id == cat_id)
            done = sum(1 for _c, ok, _d in rows if ok)
            group = Adw.PreferencesGroup(title=GLib.markup_escape_text(cat.title))
            group.set_header_suffix(chip(f"{done} / {len(rows)}", done == len(rows)))
            grid = self._icon_grid(rows)
            if grid:
                page.append(grid)
            if cat.id == "gold_skulltulas" and rows and rows[0][2]:
                info = Gtk.Label(label=f"{done} of {len(rows)} found · {rows[0][2]} · Most of them "
                                       "only come out at night.", xalign=0, wrap=True)
                info.add_css_class("dim-label")
                page.append(info)
            if any(c.group for c, _ok, _d in rows):
                shown = self._fill_grouped(page, rows)
            else:
                shown = 0
                for check, ok, detail in rows:
                    if self.filter_mode == "missing" and ok:
                        continue
                    group.add(self._check_row(check, ok, detail))
                    shown += 1
                if shown:
                    page.append(group)
        if not shown:
            page.append(Adw.StatusPage(icon_name="starred-symbolic", title="All done here!",
                                       description="Nothing left to find in this section."))
        return clamp

    def _fill_grouped(self, page: Gtk.Box, rows) -> int:
        """Rows under one sub-heading per check.group, each with its own count."""
        groups: dict[str, list] = {}
        for row in rows:
            groups.setdefault(row[0].group, []).append(row)
        shown_total = 0
        for title, members in groups.items():
            got = sum(1 for _c, ok, _d in members if ok)
            shown = [m for m in members if self.filter_mode == "all" or not m[1]]
            if not shown:
                continue
            shown_total += len(shown)
            group = Adw.PreferencesGroup(title=GLib.markup_escape_text(title))
            group.set_header_suffix(chip(f"{got} / {len(members)}", got == len(members)))
            for check, ok, detail in shown:
                group.add(self._check_row(check, ok, detail, show_detail=False))
            page.append(group)
        return shown_total

    @staticmethod
    def _check_row(check, ok: bool, detail: str, show_detail: bool = True) -> Gtk.Widget:
        sub = check.hint + (f"\n{detail}" if detail and not ok and show_detail else "")
        row = Adw.ActionRow(title=GLib.markup_escape_text(check.name), subtitle=GLib.markup_escape_text(sub.strip()))
        row.set_subtitle_lines(3)
        row.add_prefix(status_icon("yes" if ok else None))
        icon = find_icon(check.id)
        if icon:
            row.add_prefix(item_picture(icon, ok, 36))
        if ok:
            row.add_css_class("got-row")
        return row

    @staticmethod
    def _icon_grid(rows) -> Gtk.Widget | None:
        """All the category's icons at a glance: owned ones bright, missing ones faded."""
        with_icons = [(c, ok, find_icon(c.id)) for c, ok, _d in rows]
        if not any(p for _c, _ok, p in with_icons):
            return None
        grid = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True,
                           min_children_per_line=4, max_children_per_line=8,
                           column_spacing=6, row_spacing=6)
        grid.add_css_class("card")
        grid.set_margin_bottom(4)
        for check, ok, path in with_icons:
            cell = (item_picture(path, ok, 48) if path else
                    Gtk.Image(icon_name="image-missing-symbolic", pixel_size=24, opacity=0.3))
            cell.set_tooltip_text(f"{check.name} — {'got it' if ok else 'missing'}")
            cell.set_margin_top(8)
            cell.set_margin_bottom(8)
            grid.append(cell)
        return grid

    def _fill_hearts(self, page: Gtk.Box, r: mm.SlotResult) -> int:
        if r.unexplained > 0:
            page.append(self._banner("dialog-question-symbolic",
                                     f"Your hearts show {r.unexplained} more piece(s) than the save's flags "
                                     "account for. One of the pieces marked missing may already be yours."))
        info = Gtk.Label(label=f"{r.collected_count} of {mm.TOTAL_PIECES} pieces · "
                               f"{len(r.boss_containers)} of 8 boss Heart Containers. "
                               "Tap a piece for step-by-step instructions.",
                         xalign=0, wrap=True)
        info.add_css_class("dim-label")
        page.append(info)
        shown_total = 0
        for region in mm.REGIONS:
            pieces = [p for p in mm.PIECES if p.region == region]
            got = sum(1 for p in pieces if p.id in r.collected)
            shown = [p for p in pieces if self.filter_mode == "all" or p.id not in r.collected]
            if not shown:
                continue
            shown_total += len(shown)
            group = Adw.PreferencesGroup(title=GLib.markup_escape_text(region))
            group.set_header_suffix(chip(f"{got} / {len(pieces)}", got == len(pieces)))
            for p in shown:
                group.add(self._piece_row(p, r.collected.get(p.id)))
            page.append(group)
        return shown_total

    @staticmethod
    def _piece_row(p: mm.Piece, status: str | None) -> Gtk.Widget:
        row = Adw.ExpanderRow(title=GLib.markup_escape_text(p.name),
                              subtitle=GLib.markup_escape_text(p.hint))
        row.set_subtitle_lines(2)
        steps = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                        margin_top=12, margin_bottom=14, margin_start=16, margin_end=16)
        for i, text in enumerate(p.steps, 1):
            line = Gtk.Box(spacing=10)
            num = Gtk.Label(label=str(i), valign=Gtk.Align.START, width_chars=2)
            num.add_css_class("step-num")
            body = Gtk.Label(label=text, wrap=True, xalign=0, hexpand=True, selectable=True)
            body.set_wrap_mode(2)  # Pango.WrapMode.WORD_CHAR
            line.append(num)
            line.append(body)
            steps.append(line)
        row.add_row(steps)
        row.add_prefix(status_icon(status))
        if status == "yes":
            row.add_css_class("got-row")
        return row

    @staticmethod
    def _banner(icon: str, text: str) -> Gtk.Widget:
        box = Gtk.Box(spacing=10)
        box.add_css_class("card")
        box.append(Gtk.Image(icon_name=icon, margin_start=14, valign=Gtk.Align.CENTER))
        box.append(Gtk.Label(label=text, wrap=True, xalign=0, hexpand=True,
                             margin_top=10, margin_bottom=10, margin_end=14))
        return box


class TrackerApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_OPEN | Gio.ApplicationFlags.NON_UNIQUE)

    def do_startup(self):
        Adw.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def do_activate(self):
        TrackerWindow(self, None).present()

    def do_open(self, files, _n, _hint):
        path = Path(files[0].get_path()) if files and files[0].get_path() else None
        TrackerWindow(self, path).present()


def main():
    return TrackerApp().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
