--!strict
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ServerStorage = game:GetService("ServerStorage")
local Workspace = game:GetService("Workspace")

local GameConfig = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("GameConfig"))

local WaveService = {}

local randomGenerator = Random.new()
local currentWave = 0
local aliveEnemies = 0
local spawnQueue: {string} = {}
local running = false

local function buildWave(wave: number): {string}
	local total = math.min(4 + wave * 3, GameConfig.MaxWaveEnemies)
	local choices = {
		{ Name = "normal", Weight = 10 },
		{ Name = "rapido", Weight = if wave >= 2 then 4 else 0 },
		{ Name = "tirador", Weight = if wave >= 3 then 3 else 0 },
		{ Name = "tanque", Weight = if wave >= 4 then 2 else 0 },
	}
	local result = {}
	local totalWeight = 0
	for _, choice in choices do
		totalWeight += choice.Weight
	end
	for _ = 1, total do
		local roll = randomGenerator:NextNumber(0, totalWeight)
		for _, choice in choices do
			roll -= choice.Weight
			if roll <= 0 then
				table.insert(result, choice.Name)
				break
			end
		end
	end
	if wave % 5 == 0 then
		table.insert(result, "jefe")
	end
	return result
end

local function spawnEnemy(enemyType: string)
	-- El modelo se debe almacenar en ServerStorage/EnemyModels/<tipo>.
	local models = ServerStorage:FindFirstChild("EnemyModels")
	local template = models and models:FindFirstChild(enemyType)
	if not template then
		warn(string.format("[OUE] Falta el modelo ServerStorage/EnemyModels/%s", enemyType))
		return
	end

	local enemy = template:Clone()
	enemy:SetAttribute("EnemyType", enemyType)
	enemy:SetAttribute("Health", GameConfig.EnemyTypes[enemyType].Health)
	enemy.Parent = Workspace:FindFirstChild("Enemies") or Workspace
	aliveEnemies += 1
	enemy.Destroying:Connect(function()
		aliveEnemies = math.max(0, aliveEnemies - 1)
	end)
end

function WaveService.Start()
	if running then
		return
	end
	running = true
	task.spawn(function()
		while running do
			currentWave += 1
			spawnQueue = buildWave(currentWave)
			while #spawnQueue > 0 do
				if aliveEnemies < GameConfig.MaxEnemiesAlive then
					local enemyType = table.remove(spawnQueue, 1)
					spawnEnemy(enemyType)
				end
				task.wait(math.max(0.45, 1.5 - 0.06 * currentWave))
			end
			repeat
				task.wait(0.25)
			until aliveEnemies == 0 or not running
			if running then
				task.wait(GameConfig.IntermissionSeconds)
			end
		end
	end)
end

function WaveService.Stop()
	running = false
end

return WaveService
