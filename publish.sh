##!/bin/bash
#
#source ~/.alias
#
## Check if an argument is provided
#if [ -z "$1" ]; then
#    echo "Usage: $0 plots_directory_name"
#    exit 1
#fi
#
## English comment: Input directory (e.g., plots_Tau3pTauMu)
#PLOT_DIR=$1
#TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
#
## English comment: Construct the final directory name (e.g., plots_Tau3pTauMu_20260224_151209)
#TARGET_NAME="${PLOT_DIR}_${TIMESTAMP}"
#TARGET_DIR="/eos/user/y/ytakahas/${TARGET_NAME}"
#
## Check if source directory exists
#if [ ! -d "$PLOT_DIR" ]; then
#    echo "Error: Source directory ${PLOT_DIR} does not exist."
#    exit 1
#fi
#
## English comment: Create the index.html or whatever htmldir does
#htmldir ${PLOT_DIR}
#
## English comment: Create the parent directory on EOS first to avoid "No such file or directory"
#mkdir -p "/eos/user/y/ytakahas/"
#
## English comment: Copy the content. 
## Using -p ensures permissions are kept, -r for recursive
#cp -rp ${PLOT_DIR} ${TARGET_DIR}
#
#echo "Folder created at ${TARGET_DIR}"





#!/bin/bash

###source ~/.alias
###
#### Check if a directory is provided
###if [ -z "$1" ]; then
###    echo "Usage: $0 /path/to/plots_directory"
###    exit 1
###fi
###
###PLOT_DIR=${1%/}
###TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
###TARGET_DIR="/eos/user/y/ytakahas/${PLOT_DIR}_${TIMESTAMP}"
###htmldir ${PLOT_DIR}
###cp -r ${PLOT_DIR} ${TARGET_DIR}
###
###
###echo "folder created at ${TARGET_DIR}"


#!/bin/bash

source ~/.alias

# Check if a directory is provided
if [ -z "$1" ]; then
    echo "Usage: $0 /path/to/plots_directory"
    exit 1
fi

# English comment: Remove trailing slash if exists
INPUT_PATH=${1%/}

# English comment: Extract only the last directory name (e.g., /a/b/c -> c)
DIR_NAME=$(basename "$INPUT_PATH")

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# English comment: Use only the last directory name for the target path
TARGET_DIR="/eos/user/y/ytakahas/${DIR_NAME}_${TIMESTAMP}"

# English comment: Run htmldir on the original input path
htmldir "${INPUT_PATH}"

# English comment: Copy the directory to the new target location
cp -r "${INPUT_PATH}" "${TARGET_DIR}"

echo "Folder created at ${TARGET_DIR}"

