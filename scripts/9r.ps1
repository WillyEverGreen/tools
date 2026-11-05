param(
    [string]$Action = "start"
)

switch ($Action.ToLower()) {
    "start" {
        & "$PSScriptRoot\..\bin\start-9router.cmd"
    }
    "stop" {
        & "$PSScriptRoot\..\bin\stop-9router.cmd"
    }
    "status" {
        & "$PSScriptRoot\..\bin\status-9router.cmd"
    }
    "restart" {
        & "$PSScriptRoot\..\bin\stop-9router.cmd"
        Start-Sleep -Seconds 1
        & "$PSScriptRoot\..\bin\start-9router.cmd"
    }
    "open" {
        Start-Process "http://localhost:20127/dashboard"
    }
    "quota" {
        Start-Process "http://localhost:20127/dashboard/quota"
    }
    "usage" {
        Start-Process "http://localhost:20127/dashboard/usage"
    }
    "accounts" {
        node --no-warnings "D:\EXPERIMENTS PROJECTS\9router\scripts\accounts-status.mjs" @args
    }
    "test" {
        node --no-warnings "D:\EXPERIMENTS PROJECTS\9router\scripts\accounts-test.mjs" @args
    }
    "health" {
        node --no-warnings "D:\EXPERIMENTS PROJECTS\9router\scripts\accounts-status.mjs" --live @args
    }
    "update" {
        & "$PSScriptRoot\..\bin\update-9router.cmd"
    }
    "models" {
        node "d:\EXPERIMENTS PROJECTS\9router\scripts\list-models.js"
    }
    "dev" {
        Set-Location "d:\EXPERIMENTS PROJECTS\9router"
        & "d:\EXPERIMENTS PROJECTS\9router\start.cmd"
    }
    default {
        & "$PSScriptRoot\..\bin\9r.cmd" help
    }
}


