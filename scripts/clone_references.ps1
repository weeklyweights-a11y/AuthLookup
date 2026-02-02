# Run from project root
New-Item -ItemType Directory -Force -Path references | Out-Null
Set-Location references
$repos = @(
    "https://github.com/HL7-DaVinci/CDS-Library.git",
    "https://github.com/HL7-DaVinci/CRD.git",
    "https://github.com/HL7-DaVinci/dtr.git",
    "https://github.com/HL7-DaVinci/prior-auth.git",
    "https://github.com/digithree/ollama-rag.git",
    "https://github.com/QuivrHQ/MegaParse.git",
    "https://github.com/AlgorexHealth/cms-code-categorizer-python.git",
    "https://github.com/nhs-pycom/nhs-streamlit-template.git",
    "https://github.com/abhijeetk597/medical-data-extraction.git",
    "https://github.com/cpepper96/ollama-local-rag.git",
    "https://github.com/jennis0/burdoc.git"
)
foreach ($repo in $repos) {
    $name = ([uri]$repo).Segments[-1] -replace '\.git$',''
    if (-not (Test-Path $name)) {
        git clone --depth 1 $repo
    } else { Write-Host "Skipping $name (exists)" }
}
Set-Location ..
Write-Host "All reference repositories cloned to references/"
