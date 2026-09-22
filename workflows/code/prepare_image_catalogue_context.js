const rows = (name) => $(name).all().map((item) => item.json);

return [{
  json: {
    products: rows('Read Products for Image'),
    part_numbers: rows('Read Confirmed Part Numbers for Image'),
    image_evidence: rows('Read Accepted Image Evidence'),
    visual_features: rows('Read Reviewed Visual Features'),
  },
}];
