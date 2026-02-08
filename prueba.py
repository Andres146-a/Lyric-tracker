class Operaciones():
    def __init__(self, uno, dos):
        self.uno = uno
        self.dos = dos
        self.validar()
    def validar (self):
        a = self.uno
        b = self.dos
        if a != b and b != a:
            if a > b: 
                print 