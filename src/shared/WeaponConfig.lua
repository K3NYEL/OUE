--!strict
-- Compatibilidad: la tabla de armas vive en GameConfig para evitar duplicar balance.
local GameConfig=require(script.Parent:WaitForChild("GameConfig"))
return GameConfig.Weapons
