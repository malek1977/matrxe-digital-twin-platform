import { S3Client, PutObjectCommand, PutObjectCommandInput } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import crypto from "crypto";

const s3 = new S3Client({ region: process.env.AWS_REGION });

export async function presignUpload(filename: string, contentType: string, expiresIn = 60) {
  const key = `uploads/${Date.now()}-${crypto.randomBytes(6).toString('hex')}-${filename}`;
  const cmd = new PutObjectCommand({
    Bucket: process.env.S3_BUCKET!,
    Key: key,
    ContentType: contentType,
    ACL: 'private'
  } as PutObjectCommandInput);
  const url = await getSignedUrl(s3, cmd, { expiresIn });
  return { url, key };
}

export async function uploadBuffer(buffer: Buffer, key: string, contentType: string) {
  const cmd = new PutObjectCommand({
    Bucket: process.env.S3_BUCKET!,
    Key: key,
    Body: buffer,
    ContentType: contentType,
    ACL: 'private'
  });
  await s3.send(cmd);
  return key;
}
