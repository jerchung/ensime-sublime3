import sublime
import difflib

def diff_view_with_disk(view):
  old_s = open(view.file_name()).read()
  new_s = view.substr(sublime.Region(0, view.size()))
  return diff(old_s, new_s)

def diff(old_s, new_s):
  """Returns operations necessary to transform old_s into new_s.
  Note: We optimize for the (hypothetically)common case where edits will
  be localized to one small area of a large file.
  """
  limit = min(len(old_s),len(new_s))

  # Find first index (counting from the start) where the
  # strings differ.
  i = 0
  while i < limit:
    if new_s[i] != old_s[i]:
      break
    i += 1

  i = max(i-1, 0)

  # Find first index (counting from the end) where the
  # strings differ.
  j = 1
  while j < (limit - i):  # Cursors should not overlap
    if new_s[-j] != old_s[-j]:
      break
    j += 1

  j = j-1

  # Do diff, only over the modified window.
  d = difflib.SequenceMatcher(isjunk=None,
                              a=old_s[i:len(old_s) - j],
                              b=new_s[i:len(new_s) - j])

  ops = []
  for (op,i1,i2,j1,j2) in d.get_opcodes():
      # Re-add the window offset.
      k1 = i1 + i
      k2 = i2 + i
      l1 = j1 + i
      l2 = j2 + i
      if op == 'delete':
          ops.append(['-', k1, k2])
      elif op == 'insert':
          ops.append(['+', k1, new_s[l1:l2]])
      elif op == 'replace':
          ops.append(['*', k1, k2, new_s[l1:l2]])

  return ops
