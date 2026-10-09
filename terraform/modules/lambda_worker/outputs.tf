output "lambda_arn" {
  value = aws_lambda_function.order_processor.arn
}

output "lambda_name" {
  value = aws_lambda_function.order_processor.function_name
}
