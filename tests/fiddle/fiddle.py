from inf349.model import ShippingInformation

x = 0


def toto():
    global x
    x = 5


toto()

print(x)
