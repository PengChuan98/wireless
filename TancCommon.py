FiveGHzRouters = ['rtac68u','r7000','f9k1102v1','rtn66u','ea6300','sbg6580']
TwofourOnlyRouters = ['tlwr841v72','tlwr841nv11','wnr2000v2','wnr3500v1','e1200v2']

def mapRouter(router):
    if 'AC68U' in router:
        router = 'rtac68u'
    elif 'R7000' in router:
        router = 'r7000'
    elif 'SBG6580' in router:
        router = 'sbg6580'
    elif 'WR841Nv72' in router:
        router = 'tlwr841v72'
    elif 'WR841Nv11' in router:
        router = 'tlwr841nv11'
    elif 'f9k1102v1' in router:
        router = 'f9k1102v1'
    elif 'WNR2000v2' in router:
        router = 'wnr2000v2'
    elif 'WNR3500v1' in router:
        router = 'wnr3500v1'
    elif 'E1200' in router:
        router = 'e1200v2'
    elif 'RTN66U' in router:
        router = 'rtn66u'
    elif 'EA6300' in router:
        router = 'ea6300'
    else:
        print 'Select a router'
    return router
