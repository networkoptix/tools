[Reflection.Assembly]::ReflectionOnlyLoadFrom($args[0]).CustomAttributes |
Where-Object {$_.AttributeType.Name -eq "TargetFrameworkAttribute" } | 
Select-Object -ExpandProperty ConstructorArguments | 
Select-Object -ExpandProperty value
