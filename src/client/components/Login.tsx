import React from 'react';
import { Card, CardBody, Input, Button } from "@heroui/react";
import { Icon } from '@iconify/react';

const Login: React.FC = () => {
  const [email, setEmail] = React.useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Implement magic link authentication
    console.log('Magic link requested for:', email);
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <Card className="w-full max-w-md">
        <CardBody className="flex flex-col gap-4">
          <div className="text-center">
            <Icon icon="lucide:zap" className="text-primary text-4xl mb-2" />
            <h2 className="text-2xl font-bold">Welcome to Devengo</h2>
            <p className="text-default-500">Enter your email to sign in</p>
          </div>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <Input
              type="email"
              label="Email"
              placeholder="Enter your email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              startContent={<Icon icon="lucide:mail" />}
            />
            <Button color="primary" type="submit">
              Send Magic Link
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  );
};

export default Login;
