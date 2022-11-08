use resvg::ScreenSize;
use tiny_skia::Pixmap;
use tiny_skia::Transform;
use usvg::{FitTo, Options};

use crate::errors::{AppError, ErrorType};

use std::fs;


pub fn render(
    input_bytes: Vec<u8>,
    output_name: String,
    mime_type: String
) -> Result<(), AppError> {

    match render_svg(input_bytes.clone(), output_name.clone()) {
        Ok(_) => Ok(()),
        Err(_) => {
            if mime_type != "image/png" {
                Err(AppError::new("Passport has wrong format.", ErrorType::ValidationError))
            } else {
                fs::write(&format!("data/{}.png", output_name), &input_bytes).map_err(
                    |err| {
                        AppError::new(format!("Error writing passport. {}", err.to_string()).as_str(), ErrorType::ValidationError)
                    }
                )
            }
        }
    }
}


pub fn render_svg(
    input_bytes: Vec<u8>,
    output_name: String
) -> Result<(), AppError> {

    let render_tree = usvg::Tree::from_data(&input_bytes, &default_options().to_ref()).map_err(|err| {
        AppError::new(format!("Error writing passport. {}", err.to_string()).as_str(), ErrorType::ValidationError)
    })?;

    let pixmap_size = scale_size(render_tree.svg_node().size.to_screen_size(), 1);

    let mut pixmap = Pixmap::new(pixmap_size.width(), pixmap_size.height()).ok_or(
        AppError::new("Error writing passport. None", ErrorType::ValidationError)
    )?;

    resvg::render(
        &render_tree,
        FitTo::Size(pixmap_size.height(), pixmap_size.width()),
        Transform::identity(),
        pixmap.as_mut()
    ).ok_or(
        AppError::new("Error writing passport. None", ErrorType::ValidationError)
    )?;

    let png_bytes = pixmap.encode_png().map_err(|err| {
            AppError::new(format!("Error writing passport. {}", err.to_string()).as_str(), ErrorType::ValidationError)
    })?;

    fs::write(&format!("data/{}.png", output_name), &png_bytes).map_err(
            |err| {
                AppError::new(format!("Error writing passport. {}", err.to_string()).as_str(), ErrorType::ValidationError)
            }
    )
}

pub fn default_options() -> Options {
    let mut opt = usvg::Options::default();
    opt.fontdb.load_system_fonts();
    opt
}

fn scale_size(size: ScreenSize, scale: u32) -> ScreenSize {
    ScreenSize::new(size.width() * scale, size.height() * scale).unwrap()
}