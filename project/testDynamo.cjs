import AWS from 'aws-sdk';

const dynamodb = new AWS.DynamoDB.DocumentClient({ region: 'eu-west-2' });

async function testFetch() {
  try {
    const result = await dynamodb.scan({ TableName: 'FashionAnalysis' }).promise();
    console.log(result.Items);
  } catch (err) {
    console.error('DynamoDB error:', err);
  }
}

testFetch();
