param(
    [string]$Action = "start"
)

switch ($Action.ToLower()) {
    "start" {
        & "C:\tools\start-9router.cmd"
    }
    "stop" {
        & "C:\tools\stop-9router.cmd"
    }
    "status" {
        & "C:\tools\status-9router.cmd"
    }
    "restart" {
        & "C:\tools\stop-9router.cmd"
        Start-Sleep -Seconds 1
        & "C:\tools\start-9router.cmd"
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
        & "C:\tools\update-9router.cmd"
    }
    "models" {
        node "d:\EXPERIMENTS PROJECTS\9router\scripts\list-models.js"
    }
    "dev" {
        Set-Location "d:\EXPERIMENTS PROJECTS\9router"
        & "d:\EXPERIMENTS PROJECTS\9router\start.cmd"
    }
    default {
        & "C:\tools\9r.cmd" help
    }
}
