--!strict
-- OUE: servidor autoritativo. Salud, oleadas, municion, dano, compras y recompensas
-- se calculan aqui; el cliente solo solicita acciones y presenta la interfaz.
local Players = game:GetService("Players")
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local ServerStorage = game:GetService("ServerStorage")
local DataStoreService = game:GetService("DataStoreService")
local RunService = game:GetService("RunService")
local Debris = game:GetService("Debris")
local PathfindingService = game:GetService("PathfindingService")

local Config = require(ReplicatedStorage:WaitForChild("Shared"):WaitForChild("GameConfig"))
local GameService = {}

local remotes = ReplicatedStorage:FindFirstChild("OUE_Remotes") or Instance.new("Folder")
remotes.Name = "OUE_Remotes"
remotes.Parent = ReplicatedStorage
local function remote(name: string): RemoteEvent
	local item = remotes:FindFirstChild(name) or Instance.new("RemoteEvent")
	item.Name = name
	item.Parent = remotes
	return item :: RemoteEvent
end
local Action = remote("Action")
local State = remote("State")
local Notice = remote("Notice")

local recordStore = DataStoreService:GetDataStore("OUE_PlayerRecords_v1")
local enemiesFolder = workspace:FindFirstChild("OUE_Enemies") or Instance.new("Folder")
enemiesFolder.Name = "OUE_Enemies"
enemiesFolder.Parent = workspace
local effectsFolder = workspace:FindFirstChild("OUE_Effects") or Instance.new("Folder")
effectsFolder.Name = "OUE_Effects"
effectsFolder.Parent = workspace
local arenaFolder = workspace:FindFirstChild("OUE_Arena") or Instance.new("Folder")
arenaFolder.Name = "OUE_Arena"
arenaFolder.Parent = workspace

type PlayerData = {
	Points: number, Credits: number, Record: number, Kills: number, Wave: number,
	Weapon: number, Unlocked: {[number]: boolean}, Magazine: {[number]: number}, Reserve: {[number]: number},
	WeaponLevels: {[number]: {[string]: number}}, Perks: {[string]: number}, Abilities: {[string]: number},
	Cooldowns: {[string]: number}, LastShot: number, ReloadUntil: number, FuryUntil: number,
	Combo: number, ComboUntil: number, BuffUntil: number, Stamina: number, Sprinting: boolean, Paused: boolean,
	LastDash: number, LastShock: number, LastTurret: number, LastFury: number, InvulnerableUntil: number, Turrets: {Model}, Drones: {BasePart},
}
local data: {[Player]: PlayerData} = {}
local wave = 0
local intermission = 0
local spawnQueue: {string} = {}
local waveRunning = false
local random = Random.new()
local enemyCount = 0

local function newData(): PlayerData
	local mags, reserves, levels = {}, {}, {}
	for i, weapon in ipairs(Config.Weapons) do
		mags[i] = weapon.Magazine
		reserves[i] = weapon.Reserve
		levels[i] = { Damage=0, Magazine=0, FireRate=0, Reload=0 }
	end
	return {
		Points=0, Credits=0, Record=0, Kills=0, Wave=0, Weapon=1,
		Unlocked={[1]=true,[2]=true,[3]=true,[4]=false,[5]=false},
		Magazine=mags, Reserve=reserves, WeaponLevels=levels,
		Perks={Health=0,Speed=0,Fire=0,Vampire=0,Drone=0},
		Abilities={dash=0,onda=0,torreta=0,furia=0},
		Cooldowns={dash=0,onda=0,torreta=0,furia=0},
		LastShot=0,ReloadUntil=0,FuryUntil=0,Combo=0,ComboUntil=0,BuffUntil=0,
		Stamina=100,Sprinting=false,Paused=false,LastDash=0,LastShock=0,LastTurret=0,LastFury=0,InvulnerableUntil=0,Turrets={},Drones={},
	}
end

local function notify(player: Player, message: string, color: Color3?)
	Notice:FireClient(player, message, color or Color3.new(1,1,1))
end
local function humanoidOf(player: Player): Humanoid?
	local character = player.Character
	return character and character:FindFirstChildOfClass("Humanoid")
end
local function rootOf(player: Player): BasePart?
	local character = player.Character
	return character and character:FindFirstChild("HumanoidRootPart") :: BasePart?
end
local function sendState(player: Player)
	local d = data[player]
	local hum = humanoidOf(player)
	if not d then return end
	local radarEnemies = {}
	local playerRoot = rootOf(player)
	if playerRoot then
		for _, enemy in ipairs(enemiesFolder:GetChildren()) do
			if enemy:IsA("Model") and enemy.PrimaryPart and (enemy.PrimaryPart.Position-playerRoot.Position).Magnitude <= Config.RadarRange then
				table.insert(radarEnemies, enemy.PrimaryPart.Position)
			end
		end
	end
	local mags, reserves = {}, {}
	for i=1,#Config.Weapons do mags[i]=d.Magazine[i]; reserves[i]=d.Reserve[i] end
	State:FireClient(player, {
		Health=hum and hum.Health or 0, MaxHealth=hum and hum.MaxHealth or 100,
		Points=d.Points,Credits=d.Credits,Record=math.max(d.Record,d.Points),Kills=d.Kills,
		Wave=wave,Enemies=enemyCount + #spawnQueue,Intermission=intermission,RadarEnemies=radarEnemies,
		Weapon=d.Weapon,Magazine=mags,Reserve=reserves,Unlocked=d.Unlocked,
		Cooldowns={dash=math.max(0,Config.Abilities.dash.Cooldown*(.85^d.Abilities.dash)-(os.clock()-d.LastDash)),onda=math.max(0,Config.Abilities.onda.Cooldown*(.85^d.Abilities.onda)-(os.clock()-d.LastShock)),torreta=math.max(0,Config.Abilities.torreta.Cooldown*(.85^d.Abilities.torreta)-(os.clock()-d.LastTurret)),furia=math.max(0,Config.Abilities.furia.Cooldown*(.85^d.Abilities.furia)-(os.clock()-d.LastFury))},Fury=math.max(0,d.FuryUntil-os.clock()),
		Stamina=d.Stamina,Combo=d.Combo,Perks=d.Perks,Abilities=d.Abilities,
	})
end
local function award(player: Player, amount: number)
	local d=data[player]; if not d then return end
	d.Points += amount; d.Credits += amount
end
local function stat(player: Player, key: string): number
	local d=data[player]; if not d then return 0 end
	local weapon=Config.Weapons[d.Weapon]
	local level=d.WeaponLevels[d.Weapon]
	if key=="Damage" then return weapon.Damage*(1+.25*level.Damage) end
	if key=="Magazine" then return math.max(1,math.floor(weapon.Magazine*(1+.25*level.Magazine)+.5)) end
	if key=="FireRate" then return weapon.FireRate*(.9^level.FireRate) end
	if key=="Reload" then return weapon.Reload*(.85^level.Reload) end
	return 0
end
local function reserveMax(player: Player, index: number): number
	local d=data[player]; local w=Config.Weapons[index]
	return math.floor(w.MaxReserve*(1+.25*d.WeaponLevels[index].Magazine))
end
local function allAmmo(player: Player, factor: number)
	local d=data[player]; if not d then return end
	for i,w in ipairs(Config.Weapons) do
		d.Reserve[i]=math.min(reserveMax(player,i),d.Reserve[i]+math.floor(w.Magazine*2*factor))
	end
end

local function makePart(parent: Instance, name: string, size: Vector3, cf: CFrame, color: Color3, material: Enum.Material?): Part
	local p=Instance.new("Part")
	p.Name=name; p.Size=size; p.CFrame=cf; p.Color=color
	p.Material=material or Enum.Material.Slate; p.Anchored=true; p.TopSurface=Enum.SurfaceType.Smooth; p.BottomSurface=Enum.SurfaceType.Smooth
	p.Parent=parent
	return p
end

local function buildArena()
	if arenaFolder:GetAttribute("Built") then return end
	makePart(arenaFolder,"Ground",Vector3.new(84,1,84),CFrame.new(0,-.5,0),Color3.fromRGB(45,58,48),Enum.Material.Grass)
	local wallColor=Color3.fromRGB(65,68,76)
	makePart(arenaFolder,"NorthWall",Vector3.new(84,8,2),CFrame.new(0,4,-41),wallColor)
	makePart(arenaFolder,"SouthWall",Vector3.new(84,8,2),CFrame.new(0,4,41),wallColor)
	makePart(arenaFolder,"EastWall",Vector3.new(2,8,84),CFrame.new(41,4,0),wallColor)
	makePart(arenaFolder,"WestWall",Vector3.new(2,8,84),CFrame.new(-41,4,0),wallColor)
	for i=1,16 do
		local angle=random:NextNumber(0,math.pi*2)
		local radius=random:NextNumber(10,34)
		local x,z=math.cos(angle)*radius,math.sin(angle)*radius
		local sx=random:NextNumber(1.6,3.6); local h=random:NextNumber(3,7)
		local obstacle=makePart(arenaFolder,"Obstacle_"..i,Vector3.new(sx,h,sx),CFrame.new(x,h/2,z),Color3.fromRGB(75,85,105),Enum.Material.Concrete)
		obstacle:SetAttribute("Obstacle",true)
	end
	arenaFolder:SetAttribute("Built",true)
end

local function randomSpawn(): Vector3
	for _=1,50 do
		local a=random:NextNumber(0,math.pi*2); local r=random:NextNumber(23,36)
		local p=Vector3.new(math.cos(a)*r,3,math.sin(a)*r)
		local safe=true
		for _,player in ipairs(Players:GetPlayers()) do
			local root=rootOf(player)
			if root and (root.Position-p).Magnitude<18 then safe=false; break end
		end
		if safe then return p end
	end
	return Vector3.new(34,3,34)
end

local function createEnemy(kind: string): Model?
	local cfg=Config.EnemyTypes[kind]
	if not cfg then return nil end
	local model=Instance.new("Model"); model.Name=kind
	local root=Instance.new("Part"); root.Name="HumanoidRootPart"; root.Size=cfg.Size; root.Color=cfg.Color
	root.Material=Enum.Material.SmoothPlastic; root.Anchored=false; root.CanCollide=true; root.Position=randomSpawn(); root.Parent=model
	local head=Instance.new("Part"); head.Name="Head"; head.Size=Vector3.new(cfg.Size.X*.65,cfg.Size.Y*.35,cfg.Size.Z*.65)
	head.Color=Color3.fromRGB(245,225,225); head.Material=Enum.Material.Neon; head.Anchored=false; head.CanCollide=false
	head.Position=root.Position+Vector3.new(0,cfg.Size.Y*.62,0); head.Parent=model
	local weld=Instance.new("WeldConstraint"); weld.Part0=root; weld.Part1=head; weld.Parent=root
	local hum=Instance.new("Humanoid"); hum.MaxHealth=cfg.Health*(1+.12*math.max(0,wave-1)); hum.Health=hum.MaxHealth
	hum.WalkSpeed=cfg.Speed*4; hum.DisplayDistanceType=Enum.HumanoidDisplayDistanceType.None; hum.Parent=model
	model.PrimaryPart=root; model:SetAttribute("EnemyType",kind); model:SetAttribute("BaseDamage",cfg.Damage)
	model:SetAttribute("Points",cfg.Points); model:SetAttribute("Ranged",cfg.Ranged); model:SetAttribute("Shoots",cfg.Shoots)
	model.Parent=enemiesFolder
	local highlight=Instance.new("Highlight"); highlight.FillColor=cfg.Color; highlight.OutlineColor=Color3.new(1,1,1); highlight.FillTransparency=.65; highlight.Parent=model
	local healthGui=Instance.new("BillboardGui"); healthGui.Name="HealthBar"; healthGui.Size=UDim2.fromOffset(70,8); healthGui.StudsOffset=Vector3.new(0,cfg.Size.Y*.8,0); healthGui.AlwaysOnTop=true; healthGui.Parent=root
	local back=Instance.new("Frame"); back.Size=UDim2.fromScale(1,1); back.BackgroundColor3=Color3.fromRGB(25,25,25); back.BorderSizePixel=0; back.Parent=healthGui
	local fill=Instance.new("Frame"); fill.Name="Fill"; fill.Size=UDim2.fromScale(1,1); fill.BackgroundColor3=Color3.fromRGB(80,230,100); fill.BorderSizePixel=0; fill.Parent=back
	hum.HealthChanged:Connect(function(hp) fill.Size=UDim2.fromScale(math.clamp(hp/hum.MaxHealth,0,1),1) end)
	local alive=true; local lastAttack=0; local lastShot=0; local lastPath=0; local waypoints:{PathWaypoint}?=nil; local waypointIndex=2
	hum.Died:Connect(function()
		if not alive then return end; alive=false; enemyCount=math.max(0,enemyCount-1)
		local creator=hum:FindFirstChild("creator")
		local killer=creator and creator.Value
		if killer and killer:IsA("Player") and data[killer] then
			local d=data[killer]; d.Kills+=1; d.Combo+=1; d.ComboUntil=os.clock()+4
			local mult=math.min(1+math.max(d.Combo-1,0)*.1,3)
			award(killer,math.floor((cfg.Points or 10)*mult))
			if d.Perks.Vampire>0 then local kh=humanoidOf(killer); if kh then kh.Health=math.min(kh.MaxHealth,kh.Health+2*d.Perks.Vampire) end end
			if kind=="jefe" then
				for _=1,3 do
					local drop=Instance.new("Part"); drop.Shape=Enum.PartType.Ball; drop.Size=Vector3.new(.8,.8,.8); drop.Position=root.Position+Vector3.new(random:NextNumber(-2,2),2,random:NextNumber(-2,2)); drop.Anchored=true; drop.CanCollide=false; drop.Color=Color3.fromRGB(90,240,110); drop:SetAttribute("Pickup","Health"); drop.Parent=effectsFolder
				end
			end
		end
		local dropChance=random:NextNumber()
		if dropChance<.22 then
			local drop=Instance.new("Part"); drop.Name="Pickup"; drop.Shape=Enum.PartType.Ball; drop.Size=Vector3.new(.7,.7,.7); drop.Position=root.Position+Vector3.new(0,1,0); drop.Anchored=true; drop.CanCollide=false
			local choice=random:NextNumber(); local pickup=if choice<.4 then "Health" elseif choice<.85 then "Ammo" else "Damage"
			drop:SetAttribute("Pickup",pickup); drop.Color=if pickup=="Health" then Color3.fromRGB(70,255,100) elseif pickup=="Ammo" then Color3.fromRGB(255,205,55) else Color3.fromRGB(220,70,230); drop.Parent=effectsFolder
			Debris:AddItem(drop,22)
		end
		Debris:AddItem(model,2)
	end)
	task.spawn(function()
		while alive and model.Parent do
			local nearest: Player?=nil; local distance=math.huge
			for _,plr in ipairs(Players:GetPlayers()) do
				local r=rootOf(plr); local h=humanoidOf(plr)
				if r and h and h.Health>0 then local dist=(r.Position-root.Position).Magnitude; if dist<distance then nearest=plr; distance=dist end end
			end
			if not nearest then task.wait(.5); continue end
			local targetRoot=rootOf(nearest); local targetHum=humanoidOf(nearest)
			if not targetRoot or not targetHum then task.wait(.2); continue end
			local ranged=cfg.Ranged
			if (model:GetAttribute("StunnedUntil") or 0)>os.clock() then
				hum:MoveTo(root.Position)
				task.wait(.2)
				continue
			end
			if ranged then
				if distance>17 then hum:MoveTo(targetRoot.Position)
				elseif distance<9 then hum:MoveTo(root.Position-(targetRoot.Position-root.Position).Unit*7)
				else hum:MoveTo(root.Position) end
				if os.clock()-lastShot>(kind=="jefe" and 2.2 or 2.4) and distance<40 then
					lastShot=os.clock()
					local shots=if kind=="jefe" then 3 else 1
					for n=1,shots do
						local projectile=Instance.new("Part"); projectile.Shape=Enum.PartType.Ball; projectile.Size=Vector3.new(.45,.45,.45); projectile.Material=Enum.Material.Neon; projectile.Color=Color3.fromRGB(70,220,255); projectile.CanCollide=false; projectile.Anchored=false
						projectile.CFrame=CFrame.new(root.Position+Vector3.new(0,cfg.Size.Y*.65,0)); projectile.Parent=effectsFolder
						local dir=(targetRoot.Position+Vector3.new(0,1,0)-projectile.Position).Unit
						if shots==3 then dir=(CFrame.fromAxisAngle(Vector3.yAxis,(n-2)*.2):VectorToWorldSpace(dir)).Unit end
						projectile.AssemblyLinearVelocity=dir*56
						local hit=false
						projectile.Touched:Connect(function(part)
							if hit then return end
							local char=part:FindFirstAncestorOfClass("Model"); local plr=char and Players:GetPlayerFromCharacter(char)
							if plr and plr==nearest then hit=true; local pd=data[plr]; local ph=humanoidOf(plr); if ph and (not pd or os.clock()>pd.InvulnerableUntil) then ph:TakeDamage(cfg.Damage) end; projectile:Destroy() end
						end)
						Debris:AddItem(projectile,5)
					end
				end
			else
				if os.clock()-lastPath>1 then
					lastPath=os.clock()
					local path=PathfindingService:CreatePath({AgentRadius=math.max(1,cfg.Size.X/2),AgentHeight=cfg.Size.Y,AgentCanJump=true})
					local ok=pcall(function() path:ComputeAsync(root.Position,targetRoot.Position) end)
					if ok and path.Status==Enum.PathStatus.Success then
						waypoints=path:GetWaypoints()
						waypointIndex=math.min(2,#waypoints)
					else
						waypoints=nil
					end
					if waypoints and waypoints[waypointIndex] then
						local waypoint=waypoints[waypointIndex]
						if waypoint.Action==Enum.PathWaypointAction.Jump then hum.Jump=true end
						hum:MoveTo(waypoint.Position)
					else
						hum:MoveTo(targetRoot.Position)
					end
				end
				if distance<math.max(cfg.Size.X/2+2,3) and os.clock()-lastAttack>1 then lastAttack=os.clock(); local targetData=data[nearest]; if not targetData or os.clock()>targetData.InvulnerableUntil then targetHum:TakeDamage(cfg.Damage) end end
			end
			task.wait(.25)
		end
	end)
	enemyCount+=1
	return model
end

local function spawnWave()
	wave+=1; spawnQueue={}
	local total=math.min(4+wave*3,Config.MaxWaveEnemies)
	local choices={{"normal",10},{"rapido",if wave>=2 then 4 else 0},{"tirador",if wave>=3 then 3 else 0},{"tanque",if wave>=4 then 2 else 0}}
	local sum=0; for _,v in ipairs(choices) do sum+=v[2] end
	for _=1,total do
		local roll=random:NextNumber(0,sum)
		for _,v in ipairs(choices) do roll-=v[2]; if roll<=0 then table.insert(spawnQueue,v[1]); break end end
	end
	if wave%5==0 then table.insert(spawnQueue,"jefe") end
	for _,plr in ipairs(Players:GetPlayers()) do data[plr].Wave=wave; notify(plr,if wave%5==0 then "JEFE: Oleada "..wave else "OLEADA "..wave,Color3.fromRGB(255,180,70)) end
end

local function nearestEnemy(position: Vector3, range: number): Model?
	local nearest=nil; local best=range
	for _,enemy in ipairs(enemiesFolder:GetChildren()) do
		if enemy:IsA("Model") and enemy.PrimaryPart then
			local h=enemy:FindFirstChildOfClass("Humanoid")
			if h and h.Health>0 then local dist=(enemy.PrimaryPart.Position-position).Magnitude; if dist<best then best=dist; nearest=enemy end end
		end
	end
	return nearest
end
local function tagCreator(hum: Humanoid, player: Player)
	local old=hum:FindFirstChild("creator"); if old then old:Destroy() end
	local tag=Instance.new("ObjectValue"); tag.Name="creator"; tag.Value=player; tag.Parent=hum; Debris:AddItem(tag,3)
end
local function damageEnemy(player: Player, enemy: Model, amount: number, headshot: boolean?)
	local hum=enemy:FindFirstChildOfClass("Humanoid")
	if not hum or hum.Health<=0 then return end
	local d=data[player]; if not d then return end
	local final=amount*(if headshot then 2 else 1)*(if os.clock()<d.BuffUntil then 2 else 1)
	tagCreator(hum,player); hum:TakeDamage(final)
	if d.Perks.Fire>0 then
		local marker=enemy:GetAttribute("BurnUntil") or 0
		if marker<os.clock() then
			enemy:SetAttribute("BurnUntil",os.clock()+3)
			task.spawn(function() for _=1,6 do task.wait(.5); if not enemy.Parent then break end; local eh=enemy:FindFirstChildOfClass("Humanoid"); if eh and eh.Health>0 then tagCreator(eh,player); eh:TakeDamage(2+2*d.Perks.Fire) end end end)
		end
	end
end
local function explosion(player: Player, position: Vector3, radius: number, damage: number)
	local blast=Instance.new("Explosion"); blast.Position=position; blast.BlastRadius=0; blast.Parent=effectsFolder
	local ring=Instance.new("Part"); ring.Shape=Enum.PartType.Ball; ring.Size=Vector3.new(radius*2,radius*2,radius*2); ring.CFrame=CFrame.new(position); ring.Transparency=.82; ring.Color=Color3.fromRGB(255,130,40); ring.Anchored=true; ring.CanCollide=false; ring.Parent=effectsFolder; Debris:AddItem(ring,.3)
	for _,enemy in ipairs(enemiesFolder:GetChildren()) do
		if enemy:IsA("Model") and enemy.PrimaryPart then local dist=(enemy.PrimaryPart.Position-position).Magnitude; if dist<radius then damageEnemy(player,enemy,damage*(1-.5*math.clamp(dist/radius,0,1)),false) end end
	end
end

local function shoot(player: Player, direction: Vector3)
	local d=data[player]; local root=rootOf(player); local hum=humanoidOf(player)
	if not d or d.Paused or not root or not hum or hum.Health<=0 or direction.Magnitude<.8 then return end
	local now=os.clock(); local weapon=Config.Weapons[d.Weapon]
	if now-d.LastShot<stat(player,"FireRate")*.82 or now<d.ReloadUntil then return end
	local fury=now<d.FuryUntil
	if d.Magazine[d.Weapon]<=0 and not fury then notify(player,"Sin municion"); return end
	d.LastShot=now; if not fury then d.Magazine[d.Weapon]-=1 end
	local head=root.Position+Vector3.new(0,1.5,0)
	local look=root.CFrame.LookVector
	if direction.Unit:Dot(look)<-.2 then return end
	local params=RaycastParams.new(); params.FilterType=Enum.RaycastFilterType.Exclude; params.FilterDescendantsInstances={player.Character,effectsFolder}
	local damage=stat(player,"Damage"); local spread=weapon.Spread
	for _=1,weapon.Pellets do
		local offset=Vector3.new(random:NextNumber(-1,1),random:NextNumber(-1,1),random:NextNumber(-1,1))*spread
		local dir=(direction.Unit+offset).Unit; local origin=head; local remaining=120
		for _pass=1,weapon.Penetration do
			local result=workspace:Raycast(origin,dir*remaining,params)
			if not result then break end
			local target=result.Instance:FindFirstAncestorOfClass("Model")
			if weapon.Explosion>0 then explosion(player,result.Position,weapon.Explosion,damage); break end
			if target and target.Parent==enemiesFolder then
				local enemyHum=target:FindFirstChildOfClass("Humanoid")
				local isHead=result.Instance.Name=="Head"
				if enemyHum then damageEnemy(player,target,damage,isHead) end
				local travelled=(result.Position-origin).Magnitude; remaining-=travelled
				if remaining<=0 then break end
				origin=result.Position+dir*.2
			else break end
		end
	end
	if d.Magazine[d.Weapon]<=0 and d.Reserve[d.Weapon]>0 and not fury then
		local weaponIndex=d.Weapon
		local duration=stat(player,"Reload")
		local finishAt=now+duration
		d.ReloadUntil=finishAt
		task.delay(duration,function()
			if data[player]~=d or d.ReloadUntil~=finishAt then return end
			local maxMagazine=math.floor(Config.Weapons[weaponIndex].Magazine*(1+.25*d.WeaponLevels[weaponIndex].Magazine)+.5)
			local needed=math.max(0,maxMagazine-d.Magazine[weaponIndex])
			local take=math.min(needed,d.Reserve[weaponIndex])
			d.Magazine[weaponIndex]+=take; d.Reserve[weaponIndex]-=take; d.ReloadUntil=0; sendState(player)
		end)
	end
	sendState(player)
end

local function reload(player: Player)
	local d=data[player]; if not d or d.Paused then return end
	local index=d.Weapon
	local maxMagazine=math.floor(Config.Weapons[index].Magazine*(1+.25*d.WeaponLevels[index].Magazine)+.5)
	if os.clock()<d.ReloadUntil or d.Magazine[index]>=maxMagazine or d.Reserve[index]<=0 then return end
	local duration=stat(player,"Reload")
	local finishAt=os.clock()+duration
	d.ReloadUntil=finishAt
	task.delay(duration,function()
		if data[player]~=d or d.ReloadUntil~=finishAt then return end
		local needed=math.max(0,maxMagazine-d.Magazine[index])
		local take=math.min(needed,d.Reserve[index])
		d.Magazine[index]+=take; d.Reserve[index]-=take; d.ReloadUntil=0; sendState(player)
	end)
end

local function deployTurret(player: Player)
	local d=data[player]; local root=rootOf(player); if not d or not root then return end
	local level=d.Abilities.torreta; local now=os.clock()
	if now-d.LastTurret<Config.Abilities.torreta.Cooldown*(.85^level) then return end
	d.LastTurret=now
	local max=1+math.floor(level/2)
	for _,t in ipairs(d.Turrets) do if not t.Parent then table.remove(d.Turrets,table.find(d.Turrets,t) or 1) end end
	while #d.Turrets>=max do local old=table.remove(d.Turrets,1); if old then old:Destroy() end end
	local pos=root.Position+root.CFrame.LookVector*7
	local model=Instance.new("Model"); model.Name="OUE_Turret"
	local base=makePart(model,"Base",Vector3.new(1.2,.5,1.2),CFrame.new(pos),Color3.fromRGB(65,65,75),Enum.Material.Metal)
	local head=makePart(model,"Head",Vector3.new(.8,.8,.8),CFrame.new(pos+Vector3.new(0,.8,0)),Color3.fromRGB(255,135,40),Enum.Material.Neon)
	local barrel=makePart(model,"Barrel",Vector3.new(.25,.25,1.3),head.CFrame*CFrame.new(0,0,-.8),Color3.fromRGB(20,20,20),Enum.Material.Metal)
	model.PrimaryPart=base; model.Parent=workspace; table.insert(d.Turrets,model)
	local expires=now+25+5*level; local nextShot=0
	task.spawn(function()
		while model.Parent and os.clock()<expires do
			local target=nearestEnemy(base.Position,30)
			if target and target.PrimaryPart then
				head.CFrame=CFrame.lookAt(head.Position,target.PrimaryPart.Position)
				barrel.CFrame=head.CFrame*CFrame.new(0,0,-.8)
				if os.clock()>=nextShot then nextShot=os.clock()+.5*(.88^level); damageEnemy(player,target,14*(1+.35*level),false) end
			end
			task.wait(.1)
		end
		if model.Parent then model:Destroy() end
	end)
	notify(player,"Torreta desplegada",Color3.fromRGB(255,155,50))
end

local function spawnDrone(player: Player, index: number)
	local part=Instance.new("Part"); part.Name="OUE_Drone"; part.Shape=Enum.PartType.Ball; part.Size=Vector3.new(.55,.55,.55); part.Material=Enum.Material.Neon; part.Color=Color3.fromRGB(65,210,255); part.Anchored=true; part.CanCollide=false; part.Parent=workspace
	local angle=index*2.1; local nextShot=0
	task.spawn(function()
		while part.Parent and data[player] and (data[player].Perks.Drone>=index) do
			local root=rootOf(player); if not root then break end
			angle+=.04
			local targetPos=root.Position+Vector3.new(math.cos(angle)*2.4,2.6,math.sin(angle)*2.4)
			part.Position=part.Position:Lerp(targetPos,.22)
			if os.clock()>=nextShot then
				local enemy=nearestEnemy(part.Position,25)
				if enemy and enemy.PrimaryPart then nextShot=os.clock()+.8; damageEnemy(player,enemy,10,false) end
			end
			task.wait(.05)
		end
		part:Destroy()
	end)
	return part
end
local function syncDrones(player: Player)
	local d=data[player]; if not d then return end
	for _,drone in ipairs(d.Drones) do if drone then drone:Destroy() end end
	table.clear(d.Drones)
	for i=1,d.Perks.Drone do table.insert(d.Drones,spawnDrone(player,i)) end
end

local function useAbility(player: Player, key: string)
	local d=data[player]; local root=rootOf(player); local hum=humanoidOf(player); if not d or d.Paused or not root or not hum then return end
	local level=d.Abilities[key] or 0; local now=os.clock()
	if key=="dash" then
		if now-d.LastDash<5*(.85^level) then return end
		d.LastDash=now; d.InvulnerableUntil=now+.2+.02*level; local direction=hum.MoveDirection; if direction.Magnitude<.1 then direction=root.CFrame.LookVector end
		root.AssemblyLinearVelocity=Vector3.new(direction.Unit.X*70,root.AssemblyLinearVelocity.Y,direction.Unit.Z*70)
		task.delay(.22,function() if root.Parent then root.AssemblyLinearVelocity=Vector3.new(0,root.AssemblyLinearVelocity.Y,0) end end)
	elseif key=="onda" then
		if now-d.LastShock<14*(.85^level) then return end
		d.LastShock=now; local radius=9+level; local visual=Instance.new("Part"); visual.Shape=Enum.PartType.Ball; visual.Size=Vector3.new(1,1,1); visual.Position=root.Position; visual.Anchored=true; visual.CanCollide=false; visual.Transparency=.65; visual.Color=Color3.fromRGB(75,190,255); visual.Parent=effectsFolder
		game:GetService("TweenService"):Create(visual,TweenInfo.new(.4),{Size=Vector3.new(radius*2, radius*2, radius*2),Transparency=1}):Play(); Debris:AddItem(visual,.5)
		for _,enemy in ipairs(enemiesFolder:GetChildren()) do
			if enemy:IsA("Model") and enemy.PrimaryPart then local delta=enemy.PrimaryPart.Position-root.Position; if delta.Magnitude<radius then
				local eh=enemy:FindFirstChildOfClass("Humanoid"); if eh then eh:MoveTo(enemy.PrimaryPart.Position+delta.Unit*4); eh:TakeDamage(55*(1+.3*level)); enemy:SetAttribute("StunnedUntil",now+1.5) end
			end end
		end
	elseif key=="torreta" then deployTurret(player)
	elseif key=="furia" then
		if now<d.FuryUntil or now-d.LastFury<45*(.85^level) then return end
		d.LastFury=now; d.FuryUntil=now+8+2*level; notify(player,"MODO FURIA ACTIVADO",Color3.fromRGB(255,145,40))
	end
	sendState(player)
end

local function upgradeCost(base: number, level: number): number return base*(level+1) end
local function buy(player: Player, category: string, key: string, requestedIndex: number?)
	local d=data[player]; if not d then return end
	local cost=0; local action: (() -> ())?=nil
	if category=="weapon" then
		local index=tonumber(key) or (requestedIndex and math.clamp(math.floor(requestedIndex),1,#Config.Weapons)) or d.Weapon
		if not Config.Weapons[index] then return end
		local w=Config.Weapons[index]
		if tonumber(key) and not d.Unlocked[index] then
			cost=w.Price
			action=function() d.Unlocked[index]=true; d.Weapon=index end
		else
			if not d.Unlocked[index] then notify(player,"Primero desbloquea el arma"); return end
			local upgrade
			for _,item in ipairs(Config.WeaponUpgrades) do if item.Key==key then upgrade=item end end
			if not upgrade then return end
			local level=d.WeaponLevels[index][key] or 0
			if level>=5 then notify(player,"Mejora al maximo"); return end
			cost=upgradeCost(upgrade.Cost,level)
			action=function()
				d.WeaponLevels[index][key]=level+1
				if key=="Magazine" then d.Magazine[index]=math.floor(w.Magazine*(1+.25*(level+1))+.5) end
			end
		end
	elseif category=="perk" then
		local perk; for _,item in ipairs(Config.Perks) do if item.Key==key then perk=item end end
		if not perk then return end
		local level=d.Perks[key]; if level>=perk.Max then notify(player,"Mejora al maximo"); return end
		cost=upgradeCost(perk.Cost,level)
		action=function()
			d.Perks[key]=level+1
			if key=="Health" then local h=humanoidOf(player); if h then h.MaxHealth=100+20*(level+1); h.Health=math.min(h.MaxHealth,h.Health+20) end end
			if key=="Drone" then syncDrones(player) end
		end
	elseif category=="ability" then
		local ability=Config.Abilities[key]; if not ability then return end
		local level=d.Abilities[key]; if level>=ability.Max then notify(player,"Mejora al maximo"); return end
		cost=upgradeCost(({dash=200,onda=250,torreta=300,furia=300})[key],level)
		action=function() d.Abilities[key]=level+1 end
	elseif category=="supply" then
		if key=="Heal" then cost=100; action=function() local h=humanoidOf(player); if h then h.Health=h.MaxHealth end end
		elseif key=="Ammo" then cost=150; action=function() for i=1,#Config.Weapons do d.Magazine[i]=math.floor(Config.Weapons[i].Magazine*(1+.25*d.WeaponLevels[i].Magazine)+.5); d.Reserve[i]=reserveMax(player,i) end end end
	end
	if not action then return end
	if d.Credits<cost then notify(player,"Creditos insuficientes"); return end
	d.Credits-=cost; action(); notify(player,"Compra realizada",Color3.fromRGB(110,245,130)); sendState(player)
end

local function pickupTouched(pickup: BasePart, player: Player)
	local d=data[player]; if not d or pickup:GetAttribute("Collected") then return end
	pickup:SetAttribute("Collected",true)
	local kind=pickup:GetAttribute("Pickup")
	if kind=="Health" then local h=humanoidOf(player); if h then h.Health=math.min(h.MaxHealth,h.Health+35) end
	elseif kind=="Ammo" then allAmmo(player,1)
	elseif kind=="Damage" then d.BuffUntil=os.clock()+12 end
	pickup:Destroy(); notify(player,kind=="Health" and "+35 Vida" or kind=="Ammo" and "+ Municion" or "DANO DOBLE",Color3.fromRGB(110,245,130)); sendState(player)
end

local function setupPlayer(player: Player)
	local d=newData(); data[player]=d
	local ok,record=pcall(function() return recordStore:GetAsync(tostring(player.UserId)) end)
	if ok and typeof(record)=="number" then d.Record=record end
	player.CharacterAdded:Connect(function(character)
		local hum=character:WaitForChild("Humanoid") :: Humanoid
		d.Paused=false; d.Sprinting=false
		hum.MaxHealth=100+20*d.Perks.Health; hum.Health=hum.MaxHealth; hum.WalkSpeed=16*(1+.08*d.Perks.Speed)
		hum.HealthChanged:Connect(function() sendState(player) end)
		hum.Died:Connect(function()
			if d.Points>d.Record then d.Record=d.Points; pcall(function() recordStore:SetAsync(tostring(player.UserId),d.Record) end) end
			notify(player,"HAS CAIDO | Oleada "..wave.." | Puntos: "..d.Points,Color3.fromRGB(255,70,80))
		end)
		task.wait(.5); sendState(player)
	end)
	if player.Character then local h=humanoidOf(player); if h then h.MaxHealth=100; h.Health=100 end end
	task.defer(function() sendState(player) end)
end
local function cleanupPlayer(player: Player)
	local d=data[player]
	if d then
		for _,t in ipairs(d.Turrets) do if t then t:Destroy() end end
		for _,drone in ipairs(d.Drones) do if drone then drone:Destroy() end end
		if d.Points>d.Record then pcall(function() recordStore:SetAsync(tostring(player.UserId),d.Points) end) end
	end
	data[player]=nil
end

Action.OnServerEvent:Connect(function(player: Player, action: string, value: any)
	local d=data[player]; if not d or typeof(action)~="string" then return end
	if action=="Fire" and typeof(value)=="Vector3" then shoot(player,value)
	elseif action=="Reload" then reload(player)
	elseif action=="Equip" and typeof(value)=="number" then local index=math.floor(value); if d.Unlocked[index] and Config.Weapons[index] then d.Weapon=index; d.ReloadUntil=0; sendState(player) end
	elseif action=="Ability" and typeof(value)=="string" then useAbility(player,value)
	elseif action=="Shop" and typeof(value)=="table" then
		if intermission<=0 then return end
		if typeof(value.Category)=="string" and typeof(value.Key)=="string" then buy(player,value.Category,value.Key,if typeof(value.Index)=="number" then value.Index else nil) end
	elseif action=="Pause" and typeof(value)=="boolean" then d.Paused=value; if not value then sendState(player) end
	elseif action=="Sprint" and typeof(value)=="boolean" then d.Sprinting=value
	elseif action=="StartWave" then if intermission>0 then intermission=.01 end
	elseif action=="Pickup" and typeof(value)=="Instance" and value:IsA("BasePart") then
		local root=rootOf(player); if root and (root.Position-value.Position).Magnitude<8 then pickupTouched(value,player) end
	end
end)

RunService.Heartbeat:Connect(function(dt)
	for player,d in pairs(data) do
		local hum=humanoidOf(player)
		if hum and hum.Health>0 then
			if d.Paused then hum.WalkSpeed=0; d.Sprinting=false; continue end
			if d.Sprinting and d.Stamina>0 and hum.MoveDirection.Magnitude>.05 then d.Stamina=math.max(0,d.Stamina-28*dt); hum.WalkSpeed=24*(1+.08*d.Perks.Speed)
			else d.Stamina=math.min(100,d.Stamina+18*dt); hum.WalkSpeed=16*(1+.08*d.Perks.Speed) end
			if d.Stamina<=0 then d.Sprinting=false end
			if os.clock()>d.ComboUntil then d.Combo=0 end
		end
	end
	for _,pickup in ipairs(effectsFolder:GetChildren()) do
		if pickup:IsA("BasePart") and pickup:GetAttribute("Pickup") then
			for player in pairs(data) do local root=rootOf(player); if root and (root.Position-pickup.Position).Magnitude<2.5 then pickupTouched(pickup,player); break end end
		end
	end
end)

local function startWaves()
	if waveRunning then return end
	waveRunning=true
	task.spawn(function()
		while waveRunning do
			if wave==0 then
				spawnWave()
			elseif intermission>0 then
				intermission=math.max(0,intermission-1)
				for player in pairs(data) do sendState(player) end
				task.wait(1)
				if intermission<=0 then spawnWave() end
			elseif #spawnQueue>0 then
				if enemyCount<Config.MaxEnemiesAlive then
					local kind=table.remove(spawnQueue,1)
					createEnemy(kind)
					task.wait(math.max(.45,1.5-.06*wave))
				else
					task.wait(.25)
				end
			elseif enemyCount==0 then
				local bonus=100*wave
				for player in pairs(data) do
					award(player,bonus)
					local h=humanoidOf(player)
					if h then h.Health=math.min(h.MaxHealth,h.Health+15) end
					allAmmo(player,.5)
					notify(player,"Oleada superada: +"..bonus,Color3.fromRGB(110,245,130))
					sendState(player)
				end
				intermission=Config.IntermissionSeconds
			else
				task.wait(.25)
			end
		end
	end)
end

function GameService.Start()
	buildArena()
	Players.PlayerAdded:Connect(setupPlayer)
	Players.PlayerRemoving:Connect(cleanupPlayer)
	for _,player in ipairs(Players:GetPlayers()) do setupPlayer(player) end
	for _,pickup in ipairs(effectsFolder:GetChildren()) do
		if pickup:IsA("BasePart") and pickup:GetAttribute("Pickup") then pickup.Touched:Connect(function(hit)
			local plr=Players:GetPlayerFromCharacter(hit:FindFirstAncestorOfClass("Model") or hit); if plr then pickupTouched(pickup,plr) end
		end) end
	end
	startWaves()
	print("[OUE] Servidor Luau iniciado.")
end
return GameService
