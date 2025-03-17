for a in `awk '{print $1}' index`
do 
b=`grep $a index|awk '{print $2}'`

~/software/Schrodinger_Suites_2021-2/ligprep -R e -epik -ph 7.4 -pht 0.0 -isd ../wget-ligand-expo/${b}_model.sdf -osd ${a}-${b}.sdf


done
