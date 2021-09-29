const config_params = {
// default_query_template should be the local part of a url (e.g., /ermrest/catalog/1/entity/...)
// that  produces output of the form:
// {
//     "File_URL": (URL of downsampled file to fetch),
//     "RID": (RID of processed image),
//     "Source_Image": (RID of source image),
//     "Title": (title to be displayed),
//     "Downsample_Percent": (percent of file left after downsampling),
//     "PI_Name": (PI to credit),
//     "Consortium": (consortium)
// }
//
// default_consortium (optional) can be specified if the consortium isn't returned by default_query_template
//
    "default_query_template": "/ermrest/catalog/2/attribute/P:=Gene_Expression:Processed_3D_Image/RID=MY_RID/I:=Gene_Expression:Image_3D/S:=Gene_Expression:Specimen/PI:=Common:Principal_Investigator/P:RID,Source_Image:=I:RID,I:Title,PI_Name:=PI:Full_Name,P:Downsample_Percent,P:File_URL,S:Consortium"
}

