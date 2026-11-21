--!strict
local ServerScriptService=game:GetService("ServerScriptService")
local services=ServerScriptService:WaitForChild("Server"):WaitForChild("Services")
local GameService=require(services:WaitForChild("GameService"))
GameService.Start()
