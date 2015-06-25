import sublime, sublime_plugin
import Default.symbol as SublimeSymbol
from . import session
from . import diff

class ContextCheckTypeAtPoint(sublime_plugin.TextCommand):
    def run(self, edit, event):
        pt = self.view.window_to_text((event['x'], event['y']))
        s = session.for_window(self.view.window())
        s.client.type_at_point(self.view.file_name(), pt)

    def is_visible(self, event):
        return True

    def want_event(self):
        return True


class ContextInspectTypeAtPoint(sublime_plugin.TextCommand):
    def run(self, edit, event):
        pt = self.view.window_to_text((event['x'], event['y']))
        s = session.for_window(self.view.window())
        s.client.inspect_type_at_point(self.view.file_name(), pt)

    def is_visible(self, event):
        return True

    def want_event(self):
        return True


class ContextSymbolAtPoint(sublime_plugin.TextCommand):
    def run(self, edit, event):
        s = session.for_window(self.view.window())
        if self.view.is_dirty():
            d = diff.diff_view_with_disk(self.view)
            s.client.patch_source(self.view.file_name(), d)

        pt = self.view.window_to_text((event['x'], event['y']))
        s.client.symbol_at_point(self.view.file_name(), pt)

    def is_enabled(self):
        return not self.view.is_dirty()

    def is_visible(self, event):
        return True

    def want_event(self):
        return True


class TypecheckAll(sublime_plugin.WindowCommand):
    def is_enabled(self):
        return session.for_window(self.window) is not None

    def run(self):
        s = session.for_window(self.window)
        s.client.typecheck_all()

class EnsimeSave(sublime_plugin.EventListener):
    def on_post_save(self, view):
        s = session.for_window(view.window())
        if s:
            s.client.typecheck_file(view.file_name())
