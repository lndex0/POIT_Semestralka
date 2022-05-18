float value;
int i = 0;
float voltage;
float s;

void setup(){
  Serial.begin(9600);
  pinMode(9, OUTPUT);
}

void loop(){
  
  value = analogRead(A7);
  voltage = value*(5.0/1023.0);
  i = Serial.readString().toInt();
  analogWrite(9,i);
  delay(100);
  Serial.println(voltage);
}
