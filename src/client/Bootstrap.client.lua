--!strict
-- Punto de entrada del cliente. Aquí se conectarán cámara, controles y HUD.
-- La lógica de combate y recompensas permanecerá en el servidor.

local Players = game:GetService("Players")

local player = Players.LocalPlayer
print(string.format("[OUE] Cliente iniciado para %s", player.Name))
