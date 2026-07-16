from pyspark.sql import functions as F
from src.data_processing.utils.spark_utils import build_spark


def main():
    spark = build_spark("inspect-spark")
    spark.sparkContext.setLogLevel("ERROR")
    
    # Read files
    df = spark.read.option("multiline", True).json("s3a://homepedia-bronze/insee/year=2022/departement=*/population.json")
    print("DataFrame Schema:")
    df.printSchema()
    
    print(f"Total files read: {df.count()}")
    
    # Check non-null observations
    obs_count = df.filter(F.col("observations").isNotNull()).count()
    print(f"Files with observations != null: {obs_count}")
    
    # Show one row if any
    if df.count() > 0:
        df.show(1)
        
        # Show first observation's elements
        df.select(F.explode("observations").alias("o")).limit(5).show(truncate=False)
        
    spark.stop()

if __name__ == "__main__":
    main()
