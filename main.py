#!/usr/bin/env python3
"""
C4izr main entry point - Converts draw.io diagrams to C4 model format.
"""

import argparse
import os
import sys
import subprocess
import logging
from pathlib import Path

from c4izr import c4izr
import drawio_serialization
import drawio_utils

# Configure logging
logger = logging.getLogger('c4izr')
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Convert draw.io diagrams to standard C4 representation."
    )
    parser.add_argument(
        "input",
        help="Path to a .drawio file or directory containing .drawio files"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output filename (for single file) or directory (for multiple files)",
        default="output.drawio"
    )
    parser.add_argument(
        "-s", "--scaling-factor",
        type=float,
        help="Scaling factor for diagram elements (default: 1.4)",
        default=1.4
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (auto-selects first system)"
    )
    parser.add_argument(
        "--drawio-path",
        help="Path to the draw.io executable",
        default="C:\\Program Files\\draw.io\\draw.io.exe"
    )
    parser.add_argument(
        "--open-output",
        action="store_true",
        help="Open the output file(s) in draw.io after conversion"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    return parser.parse_args()

def process_file(file_path, output_path, args):
    """Process a single DrawIO file."""
    try:
        if args.verbose:
            logger.info(f"Processing: {file_path}")
        
        # Read input file
        try:
            from lxml import etree
            tree = etree.parse(file_path)
            diagrams = tree.findall('.//diagram')
            
            if len(diagrams) > 1 and args.verbose:
                logger.info(f"Multiple diagrams found in {file_path}. Converting only the first.")
            
            if not diagrams:
                logger.error(f"No diagrams found in {file_path}")
                return False
                
            xml_data = diagrams[0]
            if hasattr(xml_data, 'text') and xml_data.text and not xml_data.text.isspace():
                xml_string = drawio_serialization.decode_diagram_data(xml_data.text)
            else:
                xml_data = xml_data.find('.//mxGraphModel')
                if xml_data is None:
                    logger.error(f"No mxGraphModel found in file: {file_path}")
                    return False
                xml_string = etree.tostring(xml_data, encoding='utf-8').decode('utf-8')
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return False
        
        # Create translator with settings from args
        translator = c4izr(scaling_factor=args.scaling_factor)
        translator.interactive = not args.non_interactive
        
        # Translate the diagram
        output_xml = translator.translate(xml_string)
        
        # Write output
        try:
            data = drawio_serialization.encode_diagram_data(output_xml)
            drawio_utils.write_drawio_output(data, output_path)
            logger.info(f"Conversion successful. Output written to {output_path}")
        except Exception as e:
            logger.error(f"Error writing output to {output_path}: {str(e)}")
            return False
        
        # Open output file if requested
        if args.open_output and os.path.exists(args.drawio_path):
            try:
                subprocess.Popen([args.drawio_path, output_path])
            except Exception as e:
                logger.error(f"Error opening file in draw.io: {str(e)}")
                
        return True
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        return False

def process_directory(dir_path, output_dir, args):
    """Process all .drawio files in a directory."""
    success_count = 0
    failure_count = 0
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    for root, _, files in os.walk(dir_path):
        for filename in files:
            if filename.lower().endswith('.drawio'):
                file_path = os.path.join(root, filename)
                # Generate output path, preserving directory structure
                rel_path = os.path.relpath(file_path, dir_path)
                output_path = os.path.join(output_dir, f"c4_{rel_path}")
                
                # Ensure output directory exists
                output_file_dir = os.path.dirname(output_path)
                os.makedirs(output_file_dir, exist_ok=True)
                
                if process_file(file_path, output_path, args):
                    success_count += 1
                else:
                    failure_count += 1
    
    if args.verbose:
        logger.info(f"\nProcessing complete: {success_count} files converted successfully, {failure_count} failures")
    
    return success_count > 0

def main():
    """Main entry point for the program."""
    # Parse command line arguments
    args = parse_arguments()
    
    # Set verbose logging if requested
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Validate input path
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Error: Input path '{args.input}' does not exist.")
        return 1
    
    # Process file or directory
    if input_path.is_file():
        output_path = args.output
        return 0 if process_file(input_path, output_path, args) else 1
    elif input_path.is_dir():
        output_dir = args.output if os.path.isdir(args.output) else "c4_output"
        return 0 if process_directory(input_path, output_dir, args) else 1
    else:
        logger.error(f"Error: Input path '{args.input}' is neither a file nor a directory.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
