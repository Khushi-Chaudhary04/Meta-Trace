const { MongoClient } = require("mongodb");

const uri = "urllink";

const client = new MongoClient(uri, {
  serverSelectionTimeoutMS: 30000, // Increase timeout to 30s
  connectTimeoutMS: 30000,
});

async function testConnection() {
  try {
    await client.connect();
    console.log("✅ Successfully connected to MongoDB!");
  } catch (error) {
    console.error("❌ Connection failed:", error.message);
  } finally {
    await client.close();
  }
}

testConnection();