#!/usr/bin/env Rscript
args = commandArgs(trailingOnly=TRUE)

if (length(args)!=2) {
  stop("Two arguments must be specified (input file, output file).n", call.=FALSE)
}

# No idea how to pass these from Python...
input_dir <- args[1]
output_dir <- args[2]

dir.create(output_dir, showWarnings = FALSE)

decompose_air_seas <- function(name) {
  input_fname <- paste0(input_dir, 'gridding/seasonality-CEDS9/', name, ".Rd" )
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
