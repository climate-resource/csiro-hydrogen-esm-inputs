# No idea how to pass these from Python...
input_dir <- "/Users/znicholls/Desktop/csiro-hydrogen-esm-inputs/data/raw/emissions_downscaling_archive/gridding/"
output_dir <- "/Users/znicholls/Desktop/csiro-hydrogen-esm-inputs/data/processed/gridding/seasonality-temp/"

dir.create(output_dir, showWarnings = FALSE)

decompose_air_seas <- function(name) {
  input_fname <- paste0(input_dir, 'seasonality-CEDS9/', name, ".Rd" )
  load(input_fname)

  seas <- get( name )

  levels <- 1:dim(seas)[3]

  for (idx in levels) {
    seas_subset <- seas[,,idx,]

    out_name <- paste0(name, "_", idx)
    assign(out_name, seas_subset)


    save(list=out_name, file=paste0(output_dir, out_name, ".Rd" ))
  }
}


decompose_air_seas("AIR_BC_seasonality")
decompose_air_seas("AIR_NOx_seasonality")
