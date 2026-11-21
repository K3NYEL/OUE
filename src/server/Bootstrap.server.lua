--!strict
-- Punto de entrada del servidor Roblox.
-- Los servicios se conectan aquí para mantener el arranque predecible.

local ServerScriptService = game:GetService("ServerScriptService")

local servicesFolder = ServerScriptService:WaitForChild("Server"):WaitForChild("Services")

local WaveService = require(servicesFolder:WaitForChild("WaveService"))

WaveService.Start()
