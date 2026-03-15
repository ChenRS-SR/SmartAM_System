@echo off
chcp 65001 >nul
title 打开SLM仪表盘
echo 正在打开浏览器...
start http://localhost:5173/#/slm/dashboard
echo 已尝试打开浏览器，如果失败请手动访问上述地址
timeout /t 2 >nul
