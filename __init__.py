def classFactory(iface):
    from .skosconnect_plugin import SkosConnectPlugin
    return SkosConnectPlugin(iface)