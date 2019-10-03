@echo off
SetLocal EnableDelayedExpansion
for %%a in (%0) do set CMDDIR=%%~dpa
java -cp "%CMDDIR%\CAST-MetricsCompiler.jar;%CMDDIR%\postgresql-9.2-1004.jdbc3.jar" com.castsoftware.metricscompiler.MetricsCompilerCLI %*