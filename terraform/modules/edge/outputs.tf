output "s3_bucket_name" {
  value = aws_s3_bucket.frontend.id
}

output "cloudfront_domain_name" {
  value = aws_cloudfront_distribution.cf.domain_name
}

output "cloudfront_distribution_id" {
  value = aws_cloudfront_distribution.cf.id
}
