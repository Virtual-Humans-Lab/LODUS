param([string]$file_path='')

$isolation_values = @('0', '1')
$infection_values = @('0', '1')

$base = 'python ./simulator.py'

foreach($iso_val in $isolation_values)
{
    foreach($inf_val in $infection_values)
    {
        $cmd = $base + " --i $inf_val" + " --s $iso_val" + " --f $file_path"
        Write-Output $cmd
        #python $cmd
    }

}