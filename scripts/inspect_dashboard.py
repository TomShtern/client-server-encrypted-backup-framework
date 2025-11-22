import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from FletV2.views.dashboard import create_dashboard_view
except Exception as e:
    print('IMPORT_ERROR', e)
    raise

# Minimal dummy page that provides the attributes used by create_dashboard_view
class DummyPage:
    def __init__(self):
        self.overlay = []
        self.theme = None
        self.dark_theme = None
        self.theme_mode = None
        self.bgcolor = None
    def run_task(self, coro):
        # Do not actually schedule; return None
        return None
    def update(self):
        return None

page = DummyPage()
try:
    ctl_tuple = create_dashboard_view(None, page, None)
    # create_dashboard_view returns (control, dispose, setup_subscriptions)
    if isinstance(ctl_tuple, tuple):
        ctrl = ctl_tuple[0]
    else:
        ctrl = ctl_tuple
except Exception as e:
    print('CREATE_ERROR', e)
    raise

print('ROOT_TYPE', type(ctrl).__name__)

seen = set()

def enum_ctrl(c, depth=0, maxd=6):
    if c is None:
        print('  ' * depth + '<None>')
        return
    cid = id(c)
    if cid in seen:
        print('  ' * depth + f'<cyclic {type(c).__name__}>')
        return
    seen.add(cid)
    txt = getattr(c, 'text', None)
    exp = getattr(c, 'expand', None)
    op = getattr(c, 'opacity', None)
    info = f"{type(c).__name__} text={repr(txt)} expand={exp} opacity={op}"
    print('  ' * depth + info)
    if depth >= maxd:
        return
    children = []
    try:
        if hasattr(c, 'controls') and getattr(c, 'controls'):
            children = list(getattr(c, 'controls'))
        elif hasattr(c, 'content') and getattr(c, 'content'):
            children = [getattr(c, 'content')]
    except Exception as e:
        print('  ' * (depth+1) + f'<children inspect error: {e}>')
    for ch in children[:200]:
        enum_ctrl(ch, depth+1, maxd)

enum_ctrl(ctrl)
print('DONE')
