local retval, folder = reaper.GetUserInputs("Set JOB_DIR", 1, "Job folder path", "")
if retval and folder ~= "" then
  folder = folder:gsub("\\", "/")
  reaper.SetExtState("AI_MUSIC", "JOB_DIR", folder, true)
  reaper.ShowMessageBox("JOB_DIR saved:\n" .. folder, "OK", 0)
end