import random as ra

print("Bienvenido al juego de azar")
while True:
    for i in range(3):
        n1 = ra.randint(1, 10)
        n2 = ra.randint(1, 10)
        print (f"Adivina la multiplicación entre los números {n1} y {n2}")
        n3 = int(input(""))
        try:
            if int(n3) == n1 * n2:
                print("¡Felicidades! Has adivinado correctamente.")
            else:
                print(f"Lo siento, la respuesta correcta es {n1 * n2}.")
        except ValueError:
            print("Por favor, ingresa un número válido.")
    print("¿Deseas jugar otra vez? (s/n)")
    respuesta = input("").lower()
    while respuesta not in ["s", "n"]:
        print("Respuesta no válida. Por favor, ingresa 's' para sí o 'n' para no.")
        respuesta = input("").lower()
    if respuesta == "n":
        print("Gracias por jugar. ¡Hasta luego!")
        break
    elif respuesta == "s":
        print("¡Sigamos jugando!")
        continue
