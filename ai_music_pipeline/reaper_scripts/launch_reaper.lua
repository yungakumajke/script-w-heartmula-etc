local reaper_path = [[C:\Program Files\REAPER (x64)\reaper.exe]]
local project_path = [[C:\Users\\Pohuy\Documents\script w heartmula etc\ai_music_pipeline\reaper_template.rpp]]

local function exists(path)
  local f = io.open(path, "rb")
  if f then f:close() return true end
  return false
end

if not exists(reaper_path) then
  reaper.ShowMessageBox("REAPER exe not found:\n" .. reaper_path, "Error", 0)
  return
end

if not exists(project_path) then
  reaper.ShowMessageBox("Project not found:\n" .. project_path, "Error", 0)
  return
end

local cmd = string.format('""%s" "%s""', reaper_path, project_path)
os.execute(cmd)