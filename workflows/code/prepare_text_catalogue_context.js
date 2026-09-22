const rows = (name) => $(name).all().map((item) => item.json);

return [{
  json: {
    products: rows('Read Products'),
    part_numbers: rows('Read Confirmed Part Numbers for Text'),
    image_evidence: [],
    visual_features: [],
  },
}];
