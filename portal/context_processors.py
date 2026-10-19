from .catalog import MODULES

def catalog(request):
    return {'sidebar_modules': MODULES}
